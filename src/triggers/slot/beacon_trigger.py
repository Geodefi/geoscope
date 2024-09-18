# -*- coding: utf-8 -*-


from src.classes import Trigger
from src.globals import get_constants
from src.helpers.slots import fetch_slots_batch
from src.helpers.withdrawals import filter_withdrawals_batch, process_many_withdrawals
from src.helpers.deposits import filter_deposits_batch, process_many_deposits
from src.database.slots import insert_many_slots, get_max_slot, fetch_block_number
from src.database.deposits import insert_many_deposits
from src.database.withdrawals import insert_many_withdrawals
from src.database.validators import update_portal_validators
from src.helpers.merkle import (
    should_update_merkle,
    build_balances_data,
    prepare_report,
    report_beacon,
)


class BeaconTrigger(Trigger):
    """Processes updates from both execution and consensus chain for all slots between
        the configured start slot and the latest periodically detected slot.

    Attributes:
        name (str): name of the trigger to be used when logging etc. (value: BEACON)
    """

    name: str = "BEACON"

    def __init__(self) -> None:
        """Initializes a BeaconTrigger object.
        The trigger will process the changes of the daemon after a loop.
        It is a callable object. It is used to process the changes of the daemon.
        It can only have 1 action:
            indexing all slots between the configured start slot
            and the latest periodically detected slot.
        """

        Trigger.__init__(self, name=self.name, action=self.index_slots)

    def index_slots(self, curr_slot_num, *args) -> None:
        """
        1. Indexes and saves all required slot data to db
            - do it once! (unless db is wiped out with '--reset' flag)
            - can restore from db in case of a restart.
        2. fetches and saves validator data from portal
        3. processes deposits, filters according to the portal and saves.
        4. processes withdrawals, filters according to the portal and saves.
        5. updates validator states from beaconchain
        6. updates validator balances from beaconchain
        """
        fallback_slot: int = int(get_constants().chain.start.slot)
        db_slot_num: int = get_max_slot(fallback_slot)

        slot_process_steps: int = 10000  # TODO: config.json this
        for i in range(db_slot_num, curr_slot_num + 1, slot_process_steps):
            # Processing slots in batches, we can not just try to do it at once!
            last_slot_num: int = min(i + slot_process_steps, curr_slot_num)
            # So, since we are getting the latest processed slot here, we should actually **SAVE** it at the
            # last point where we are done processing the validators, deposits and withdrawals.
            gathered_slots = fetch_slots_batch(first_slot=i, last_slot=last_slot_num)

            update_portal_validators(
                first_block=gathered_slots[0]["block_number"],
                last_block=gathered_slots[-1]["block_number"],
            )

            deposits: list[dict] = filter_deposits_batch(gathered_slots)
            if deposits:
                process_many_deposits(curr_slot_num, deposits)
                insert_many_deposits(deposits)

            withdrawals: list[dict] = filter_withdrawals_batch(gathered_slots)
            if withdrawals:
                process_many_withdrawals(withdrawals)
                insert_many_withdrawals(withdrawals)

            # TODO: process slots and update fee_recipient balances here...
            # Note that when we are sending the merkle roots, we include it in withdrawn_balance

            insert_many_slots(gathered_slots)

        block_number = fetch_block_number()
        self.process_report_beacon(block_number)

    def process_report_beacon(self, block_number: int):
        # TODO: this should take block number of the curr_slot_num
        should_update, prices = should_update_merkle("haha")
        if should_update:
            balances: dict = build_balances_data
            price_merkle_root, balance_merkle_root, all_validators_count = prepare_report(
                prices, balances
            )
            report_beacon(price_merkle_root, balance_merkle_root, all_validators_count)
