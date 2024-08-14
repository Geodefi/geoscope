# -*- coding: utf-8 -*-

from itertools import repeat
from src.classes import Trigger
from src.daemons import TimeDaemon
from src.utils.thread import multithread
from src.database.validators import fill_validators_table
from src.globals import get_logger
from src.helpers.validator import ping_pubkey_balance, ping_pubkey_status


# TODO: (later) Stop and throw error after x attempts: This should be fault tolerant.
class ExpectPubkeysTrigger(Trigger):
    """Trigger for the EXPECT_PUBKEYS.
    A time trigger that waits for a list of pubkeys, and checks if any can be filtered
    according to the provided filter function. Works every 15 minutes.
    Initial delay can be provided.
    Can stop the daemon after all the validators are recorded in db, if keep_alive is False.

    Attributes:
        name (str): The name of the trigger to be used when logging etc. (value: EXPECT_DEPOSIT)
        __balance (int): When provided, the pubkeys will be filtered by the balance when detected.
        __status (str): When provided, the pubkeys will be filtered by the status when detected.
        __pubkeys (str): Internal list of validator pubkeys to be finalized when ALL exited.
        __keep_alive (str): TimeDaemon will not be shot down when pubkeys list is empty.
        Useful for event listeners.
    """

    name: str = "EXPECT_PUBKEYS"

    def __init__(
        self,
        balance: int = None,
        status: str = None,
        pubkeys: list[str] = [],
        keep_alive: bool = False,
    ) -> None:
        Trigger.__init__(self, name=self.name, action=self.process_deposits)
        self.__balance: int = balance
        self.__status: int = status
        self.__pubkeys: str = pubkeys
        self.__keep_alive: bool = keep_alive
        get_logger().debug(f"{self.name} is initated.")

    def append(self, pubkeys: str, daemon: TimeDaemon = None):
        """Extends the internal pubkeys list provided list with 1 pubkey
            then immadiately processes the current list.

        Args:
            pubkey (str): pubkey to append into pubkeys list
            daemon (TimeDaemon): daemon to be stopped if the pubkey is empty
        """
        self.__pubkeys.append(pubkeys)
        self.process_deposits(daemon)

    def extend(self, pubkeys: str, daemon: TimeDaemon = None):
        """Extends the internal pubkeys list with provided list of more pubkeys
        then immadiately processes the current list.

        Args:
            pubkeys (list[str]): list of pubkeys to append into pubkeys list
            daemon (TimeDaemon): daemon to be stopped if the pubkey is empty
        """
        self.__pubkeys.extend(pubkeys)
        self.process_deposits(daemon)

    # pylint: disable-next=unused-argument
    def process_deposits(self, *args, daemon: TimeDaemon = None, **kwargs) -> None:
        """Checks if any of the expected pubkeys are responding after the proposal deposit.
        Processes the ones that respond and keeps the ones that don't for the next iteration.

        Args:
            daemon (TimeDaemon): daemon to be stopped if the pubkey is empty
        """
        if self.__pubkeys:

            filtered = self.__pubkeys
            if self.__balance:
                filtered: bool = multithread(ping_pubkey_balance, filtered, repeat(self.__balance))

            if self.__status:
                filtered: bool = multithread(ping_pubkey_status, filtered, repeat(self.__status))

            responded = []
            remaining = []
            for pk, res in zip(self.__pubkeys, filtered):
                if res:
                    responded.append(pk)
                else:
                    remaining.append(pk)

            if len(responded) > 0:
                fill_validators_table(responded)

            if len(remaining) > 0:
                self.__pubkeys = remaining

        if not self.__keep_alive and daemon:
            daemon.stop()
