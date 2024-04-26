
from hexbytes import HexBytes
from eth_typing import ChecksumAddress

from globals.env import PRIVATE_KEY
from globals.w3 import W3
from globals.exceptions import InvalidPrivateKeyException


class Owner(object):

    def __init__(self):
        if (PRIVATE_KEY is None):
            self.address = "OWNER_PRIVATE_KEY_WAS_NOT_PROVIDED"
        else:
            try:
                address = W3.eth.account.from_key(PRIVATE_KEY).address
            except:
                raise InvalidPrivateKeyException(
                    "Oracle object cannot be created due to Invalid Private Key")

            if not W3.is_checksum_address(address):
                address = W3.to_checksum_address(address)

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
        return W3.eth.get_balance(self.address)

    def getNonce(self) -> int:
        """
        returns: the nonce value (transaction count)
        """
        return W3.eth.get_transaction_count(self.address)
