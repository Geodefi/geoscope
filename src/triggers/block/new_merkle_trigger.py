# -*- coding: utf-8 -*-

from itertools import repeat
from geodefi.globals import DEPOSIT_SIZE, BEACON_DENOMINATOR, ETHER_DENOMINATOR

from src.logger import log
from src.classes import Trigger
from src.globals import SDK
from src.helpers import (
    create_validators_table,
    save_beacon_balances,
    get_all_pool_ids,
    fetch_balances_by_pool_id_batch,
    fetch_active_vals,
)
from src.utils import multithread, get_epoch
from src.actions import call_reportBeacon


class NewMerkleTrigger(Trigger):
    """Every day checks for balance and price merkles.

    Attributes:
        name (str): name of the trigger to be used when logging etc. (value: MERKLE)
    """

    name: str = "MERKLE"

    def __init__(self) -> None:
        """Initializes a MerkleTrigger object. The trigger will process the changes of the daemon after a loop.
        It is a callable object. It is used to process the changes of the daemon. It can only have 1 action.
        """

        Trigger.__init__(
            self, name=self.name, action=self.price_and_balance_merkle
        )
        create_validators_table()
        log.debug(f"{self.name} is initated.")

    def __update_beacon_balances(self, vals: list[tuple]):
        epoch = get_epoch()["epoch"]
        beacon_balances = multithread(
            self.__process_beacon_balance, vals, repeat(epoch)
        )
        if beacon_balances:
            save_beacon_balances(vals, beacon_balances)

    def __process_beacon_balance(
        self, pk_index_tuple: tuple, current_epoch: str
    ) -> str:
        # THERE CAN BE 2 TYPE OF VALIDATORS HERE:
        #
        # 1. Deposited 31 eth, have not been reflected yet : beacon.status = deposited, pending:
        # -> beacon(validator).balance is 1 eth.
        # -> safe to assume 31 eth is still on the way.
        #
        # 2. Deposited and processed the 31 eth : any other status
        # -> utilize beacon(validator).balance
        # -> check if slashed or exited : then beacon_balance is assumed to be ZERO !important

        # pk_index_tuple[0] is the pubkey
        v = SDK.portal.validator(pk_index_tuple[0])
        status = v.beacon_status
        balance = v.balance
        # withdrawn = v.total_withdrawals

        # TODO: lets do not use assert? lets use if else so we can take actions
        #       or throw an exception if it is not as expected?

        if status == "deposited":
            # TODO: if deposit size 1e9 (which is currently like that) then no need to divide by beacon_denominator
            #       devide by beacon_denominator if deposit size is 1e18
            assert balance == DEPOSIT_SIZE.PROPOSAL

            # TODO: discuss isnt should be DEPOSIT_SIZE.PROPOSAL + DEPOSIT_SIZE.STAKE ?
            balance = DEPOSIT_SIZE.STAKE

        elif status == "pending":
            # TODO: discuss isnt should be DEPOSIT_SIZE.PROPOSAL + DEPOSIT_SIZE.STAKE ?
            assert balance == DEPOSIT_SIZE.STAKE

        elif status == "slashed" or status == "exited":
            assert current_epoch >= v.exit_epoch
            if current_epoch >= v.withdrawable_epoch:
                balance = 0

        return str(balance)

    def __calc_price(self, id: str, balances: dict) -> int:
        pool = SDK.portal.pool(int(id))
        # TODO_task: TAKE THE LATEST GIVEN BLOCK WHEN CALCULATING
        surplus = pool.surplus
        # TODO_task: TAKE THE LATEST GIVEN BLOCK WHEN CALCULATING
        secured = pool.secured
        # TODO_task: TAKE THE LATEST GIVEN BLOCK WHEN CALCULATING
        supply = SDK.token.contract.functions.totalSupply(int(id)).call()
        # TODO: create fetch balance for id function to use below
        price = (
            (
                (
                    balances["beacon_balance"]
                    + balances["withdrawn_balance"]
                    + balances["fee_recipient_balance"]
                )
                * BEACON_DENOMINATOR
                + (surplus + secured)
            )
            * ETHER_DENOMINATOR
        ) // supply

        return price

    def __calc_prices_batch(self) -> dict:
        ids: list = get_all_pool_ids()

        # get all balances
        balances = fetch_balances_by_pool_id_batch(
            ids, ["depositing, active"]
        )  # TODO: discuss the states

        prices = multithread(self.__calc_price, ids, balances)
        return dict(zip(ids, prices))

    def price_and_balance_merkle(self, *args, **kwargs) -> None:
        """Checks for balance and price merkles and updates the database, sends post request to the API and
        transaction to the blockchain to update the merkles.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        log.info(f"{self.name} is triggered.")

        # TODO: merkle implementation

        # get all active pks and their beacon_index (will use it while updating withdrawn balances)
        # TODO: from the database (discuss which states count as active)
        active_vals: list[tuple] = fetch_active_vals()

        # update beacon balances
        self.__update_beacon_balances(active_vals)

        # update withdrawn balances

        # update fee recepient balances

        # calculate prices
        prices = self.__calc_prices_batch()

        # check ts is valid to update chain
        # check price change is in the range
        # get total validator count
        # create merkle tree
        price_merkle_root = "0x1234"
        balances_merkle_root = "0x5678"
        all_validators_count = 100

        # update chain
        call_reportBeacon(
            price_merkle_root, balances_merkle_root, all_validators_count
        )


# TODO: triggers that needs to be created to be able to run the merkle trigger
#       - staked trigger (event trigger) (to get the staked validators and update the database)
#       - withdrawals_and_fee_recepient trigger (block trigger) (to get the withdrawn validators and update the database)
