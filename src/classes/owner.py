from hexbytes import HexBytes
from eth_typing import ChecksumAddress

from src.globals import get_env, get_sdk
from src.exceptions.globals.sdk import InvalidPrivateKeyError


class Owner(object):

    def __init__(self):
        if get_env().PRIVATE_KEY is None:
            self.address = "OWNER_PRIVATE_KEY_WAS_NOT_PROVIDED"
        else:
            try:
                address = (
                    get_sdk()
                    .w3.eth.account.from_key(get_env().PRIVATE_KEY)
                    .address
                )
            except Exception as e:
                raise InvalidPrivateKeyError(
                    "Oracle object cannot be created due to Invalid Private Key"
                ) from e

            if not get_sdk().w3.is_checksum_address(address):
                address = get_sdk().w3.to_checksum_address(address)

            self.private_key = get_env().PRIVATE_KEY
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
        return get_sdk().w3.eth.get_balance(self.address)

    def getNonce(self) -> int:
        """
        returns: the nonce value (transaction count)
        """
        return get_sdk().w3.eth.get_transaction_count(self.address)
