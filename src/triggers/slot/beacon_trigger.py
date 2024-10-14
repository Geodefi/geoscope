# -*- coding: utf-8 -*-

from typing import Iterator
from src.classes import Trigger
from src.helpers.slots import fetch_slots_batch
from src.helpers.withdrawals import filter_withdrawals_batch, process_withdrawals_batch
from src.helpers.deposits import filter_deposits_batch, process_deposits_batch
from src.helpers.portal import update_portal_pools
from src.database.slots import insert_slots_batch, read_max_slot, read_block_number
from src.database.deposits import insert_deposits_batch
from src.database.withdrawals import insert_withdrawals_batch
from src.database.validators import (
    update_portal_validators,
    read_proposed_validators,
)
from src.database.pools import read_pool_ids
from src.helpers.merkle import gather_merkle_data, prepare_report
from src.helpers.validators import should_verify_validators, verify_validators_batch
from src.helpers.fee_recipient import process_fee_recipients
from src.database.merkles import insert_merkle_tree_json

from src.helpers.portal import handle_report_beacon, handle_update_verification_index


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

        Trigger.__init__(self, name=self.name, action=self.process_slots)

    # pylint: disable-next=unused-argument
    def process_slots(self, curr_slot_num, *args) -> None:
        """Indexes and saves all required slot data to db: Deposits, Withdrawals, Slots.
            Then checks if there are any actions to take after the fresh update.

        Args:
            curr_slot_num (_type_): _description_
        """
        self.index_slots(curr_slot_num)

        db_latest_block_number = read_block_number(curr_slot_num)

        self.process_report_beacon(curr_slot_num, db_latest_block_number)

        self.process_verifications(curr_slot_num, db_latest_block_number)

    # pylint: disable-next=unused-argument
    def index_slots(self, curr_slot_num, *args) -> None:
        """Indexes and saves all required slot data to db
            - do it once! (unless db is wiped out with '--reset' flag)
            - can restore from db in case of a restart.
        1. Fetches and saves new validators from portal.
        2.1 Processes deposits, filters according to the portal and saves.
        2.2 Updates constant validator data from beaconchain
        3.1 Processes withdrawals, filters according to the portal and saves.
        3.2 Updates total withdrawal amount for the validators
        3.2 Saves slot data to Slots table on database

        Args:
            block_number (int): _description_
        """
        db_slot_num: int = read_max_slot()

        gathered_slots: list[dict] = fetch_slots_batch(
            first_slot=db_slot_num, last_slot=curr_slot_num
        )

        update_portal_pools(gathered_slots[-1]["block_number"])

        update_portal_validators(
            first_block=gathered_slots[0]["block_number"],
            last_block=gathered_slots[-1]["block_number"],
        )

        deposits: list[dict] = filter_deposits_batch(gathered_slots)
        if deposits:
            process_deposits_batch(curr_slot_num, deposits)
            insert_deposits_batch(deposits)

        withdrawals: list[dict] = filter_withdrawals_batch(gathered_slots)
        if withdrawals:
            process_withdrawals_batch(withdrawals)
            insert_withdrawals_batch(withdrawals)

        # Since we are getting the latest processed slot here,
        # we should actually **SAVE** it at the last point where we are done
        # processing the validators, deposits and withdrawals:
        insert_slots_batch(gathered_slots)

        # After processing the changes on validators and inserting the slots
        # we will process the fee_recipients:
        process_fee_recipients(db_slot_num)

    def process_report_beacon(self, slot_number: int, block_number: int):

        pool_ids: list[int] = read_pool_ids()
        should_update, prices_data = gather_merkle_data(pool_ids, block_number, slot=slot_number)

        if should_update:
            price_iterator: Iterator = iter(([pool[0], pool[1]] for pool in prices_data))
            balance_iterator: Iterator = iter(
                ([val[0], val[7], val[4] + val[6]] for pool in prices_data for val in pool[2])
            )

            price_merkle_root, balance_merkle_root, all_validators_count = prepare_report(
                balance_iterator, price_iterator
            )

            success: bool = handle_report_beacon(
                price_merkle_root, balance_merkle_root, all_validators_count
            )

            if success:
                insert_merkle_tree_json(price_merkle_root, price_iterator)
                insert_merkle_tree_json(balance_merkle_root, balance_iterator)

    def process_verifications(self, slot_number: int, block_number: int):
        """
        1. Detects validators to verify
        2. Checks if it is yet the right time to verify
        3. Verifies
        4. Updates verification index accordingly
        Args:
            block_number (int): block number to be
        """

        pending_validators: list[tuple] = read_proposed_validators(block_identifier=block_number)

        aliens = []
        if should_verify_validators(slot_number, pending_validators):
            aliens = verify_validators_batch(pending_validators, block_identifier=block_number)

        new_verification_index: int = max(pending_validators, key=lambda x: x["portal_index"])

        success: bool = handle_update_verification_index(new_verification_index, aliens)
