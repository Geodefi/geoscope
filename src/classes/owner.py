from hexbytes import HexBytes
from eth_typing import ChecksumAddress

from src.globals.env import PRIVATE_KEY
from src.globals.sdk import SDK
from src.exceptions.globals.sdk import InvalidPrivateKeyError


class Owner(object):

    def __init__(self):
        if PRIVATE_KEY is None:
            self.address = "OWNER_PRIVATE_KEY_WAS_NOT_PROVIDED"
        else:
            try:
                address = SDK.w3.eth.account.from_key(PRIVATE_KEY).address
            except Exception as e:
                raise InvalidPrivateKeyError(
                    "Oracle object cannot be created due to Invalid Private Key"
                ) from e

            if not SDK.w3.is_checksum_address(address):
                address = SDK.w3.to_checksum_address(address)

            self.private_key = PRIVATE_KEY
            self.address = address

    def __str__(self):
        return f"{self.address}"

    def getPrivateKey(self):
        return self.private_key

    def getAddress(self) -> ChecksumAddress:
        return self.address

    def getBalance(self) -> int:
        """
        returns: the balance of the account
        """
        return SDK.w3.eth.get_balance(self.address)

    def getNonce(self) -> int:
        """
        returns: the nonce value (transaction count)
        """
        return SDK.w3.eth.get_transaction_count(self.address)
