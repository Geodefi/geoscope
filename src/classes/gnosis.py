import os
import json
from typing import List, Any
from time import sleep

import requests
from web3.exceptions import ContractLogicError
from web3.contract import Contract
from eth_account import Account
from eth_abi import encode, is_encodable
from eth_typing import ChecksumAddress
from hexbytes import HexBytes

from src.exceptions.classes.gnosis import (
    WatcherError,
    ContractCreationError,
)
from src.globals.config import CONFIG
from src.globals.sdk import SDK
from src.globals.constants import NULL_ADDRESS, WATCHER_URLS, ATTEMPT

# from script.helpers import gasPrice

from .owner import Owner


class Gnosis(object):

    def __init__(self, caller: Owner):
        """
        :param caller: Owner registered to system.
        :param methodid: MethodId of ReportOracle function
        """

        self.caller: Owner = caller

        gnosis_abi_path = os.path.join(
            CONFIG.abi_directory.folder_name, CONFIG.abi_directory.files.gnosis
        )

        # Get ABI
        with open(gnosis_abi_path, "r") as file:
            a = file.read()
        abi = json.loads(a)

        # Get address and abi from json
        try:
            address = abi["address"]
            if not SDK.w3.is_checksum_address(address):
                address = SDK.w3.to_checksum_address(address)

            self.safe_address: ChecksumAddress = address
            self.abi = abi["abi"]

        except KeyError:
            raise ContractCreationError(
                "GeodeFinance: Please provide correct Gnosis abi and contract address in abi/.json"
            )

        try:
            self.gnosisContract: Contract = SDK.w3.eth.contract(
                abi=self.abi, address=self.safe_address
            )
        except:
            raise ContractCreationError(
                "GeodeFinance: Gnosis- Invalid ABI or Contract Address"
            )

        # LOGGER.debug(f"The Gnosis is found at      : {self.safe_address}")

    def sendTx(
        self,
        contract_address: ChecksumAddress,
        method_id: str,
        param_types: List[str],
        param_args: List[Any],
    ):
        """
        :param contract_address: The address of target contract. (Not Safe contract)
        :param PLANET_ID: The registered Planet ID
        :param OPERATOR_ID: The list of target opearators.
        :param balanceIncrease: The list of how much avax has been gained by staking per operator.
        """

        assert len(param_types) == len(
            param_args
        ), "The types and args must have same length."
        assert is_encodable(
            param_types, param_args
        ), "The types and args are not encodable."

        encoded_data = method_id + encode(param_types, param_args).hex()

        # get Nonce
        safe_nonce = self.getNonce()
        # LOGGER.debug(f"Nonce of Gnosis Safe is {safe_nonce}.")

        # get Tx Hash
        try:
            safe_tx_hash: HexBytes = self.getTransactionHash(
                contract_address, encoded_data, safe_nonce
            )
        except:
            raise

        # sign
        signature = self.sign(safe_tx_hash, self.caller.getPrivateKey())

        # execution
        success: int = 0
        tx_receipt = None
        try:
            success, tx_receipt = self.execTransaction(
                contract_address, encoded_data, signature
            )

        except ContractLogicError as e:
            # This spesific error is related with gnosis gas fees.
            if str(e) == "execution reverted: GS026":
                raise  # TODO: This error should be handled!
            else:
                # LOGGER.warning(f"This error has been ignored: {e}")
                pass

        return success, tx_receipt

    def getHashAndSignature(
        self,
        contract_address: ChecksumAddress,
        method_id: str,
        param_types: List[str],
        param_args: List[Any],
    ):
        # get nonce

        safe_nonce = self.getNonce()

        assert len(param_types) == len(
            param_args
        ), "The types and args must have same length."
        assert is_encodable(
            param_types, param_args
        ), "The types and args are not encodable."

        # form data =
        encoded_data = method_id + encode(param_types, param_args).hex()

        # form Transaction hash by optimistic balance increase
        txHash = self.getTransactionHash(
            to=contract_address, data=encoded_data, nonce=safe_nonce
        )

        # get signature
        privkey = self.caller.getPrivateKey()
        signature = self.sign(tx_hash=txHash, private_key=privkey)

        return txHash, signature, encoded_data, safe_nonce

    def sendTxToWatchers(
        self,
        contract_address: ChecksumAddress,
        method_id: str,
        param_types: List[str],
        param_args: List[Any],
    ):
        # SEND TO WATCHERs

        txHash, signature, encoded_data, safe_nonce = self.getHashAndSignature(
            contract_address, method_id, param_types, param_args
        )

        # FIX ME AFTER THE WATCHER UPDATE

        # the safe tx hash and signature is enough to call execTransaction fucntion in gnosis contract.
        # The others have been sent to verify in the server side too.

        payload = {
            "safe_nonce": safe_nonce,
            "txHash": txHash,
            "signature": signature,
            "data": encoded_data,
        }

        for watcher_url in WATCHER_URLS:
            count = 0
            while True:
                try:
                    res = requests.post(watcher_url, params=payload)
                    break
                except:
                    if count < ATTEMPT:
                        sleep(1)
                        count += 1
                    else:
                        raise WatcherError(
                            f"GeodeFinance: Couldn't get the data after {count} attempts."
                        )

            if res.status_code == 500:
                raise WatcherError(f"The status code is {res.status_code}.")

            # def parseResponse():
            #    # TODO BE IMPLEMENTED (and moved to somewhere else)
            #    pass

            # success, tx_receipt = parseResponse(res.content)
            # return success, tx_receipt
            return 1, {}

    def sign(self, tx_hash: HexBytes, private_key: HexBytes) -> HexBytes:
        """
        :param tx_hash: hex-encoded safe transaction to sign
        :param private_key: hex-encoded private key
        """
        contract_transaction_hash = HexBytes(tx_hash)
        account = Account.from_key(private_key)

        # Sign
        signature = account.signHash(contract_transaction_hash)

        # Return in hex-encoded
        return signature.signature.hex()

    def getNonce(self) -> int:
        """
        :returns nonce: the nonce value of safe-contract
        """
        return int(self.gnosisContract.functions.nonce().call())

    def getTransactionHash(
        self, to: ChecksumAddress, data: HexBytes, nonce: int
    ) -> HexBytes:
        """
        :param to: address of target contract (portal)
        :param data: hex-encoded input data
        :param nonce: the nonce value of safe-contract

        :returns: hex-encoded transaction hash
        """

        return SDK.w3.to_hex(
            self.gnosisContract.functions.getTransactionHash(
                to,
                0,  # value
                data,
                0,  # operation
                0,  # safeTxGas
                0,  # baseGas
                0,  # gasPrice
                NULL_ADDRESS,  # gasToken
                NULL_ADDRESS,  # refundReceiver
                nonce,
            ).call()
        )

    def execTransaction(
        self, to: ChecksumAddress, data: HexBytes, signatures: str
    ):
        """
        :param to: address of target contract (portal)
        :param data: hex-encoded input data
        :param signatures: the results of sign by each owner concatted.
        """
        tx = self.gnosisContract.functions.execTransaction(
            to,
            0,  # value
            data,
            0,  # operation
            0,  # safeTxGas
            0,  # baseGas
            0,  # gasPrice
            NULL_ADDRESS,  # gasToken
            NULL_ADDRESS,  # refundReceiver
            signatures,
        ).buildTransaction({"from": self.caller.getAddress()})

        tx["nonce"] = self.caller.getNonce()
        privateKey = self.caller.getPrivateKey()

        signed = SDK.w3.eth.account.sign_transaction(tx, privateKey)
        tx_hash = SDK.w3.eth.sendRawTransaction(signed.rawTransaction)

        # LOGGER.debug("TX has been sent. Waiting for receipt...")
        tx_receipt = SDK.w3.eth.waitForTransactionReceipt(tx_hash)

        if tx_receipt.status == 1:
            # LOGGER.info(
            #     f"TX successful: {dict(tx_receipt)['transactionHash'].hex()}")
            return 1, tx_receipt
        else:
            # LOGGER.error(
            #     f"TX reverted: {dict(tx_receipt)['transactionHash'].hex()}")
            return 0, tx_receipt
