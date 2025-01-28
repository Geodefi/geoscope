from typing import Any

from eth_typing import HexStr

from src.actions.portal import (
    handle_regulate_operators,
    handle_report_beacon,
    handle_update_verification_index,
)
from src.classes import Trigger
from src.common import BigInteger
from src.database.deposits import insert_deposits_batch
from src.database.merkles import insert_merkle_tree_json
from src.database.pools import read_pool_ids
from src.database.slots import insert_slots_batch, read_block_number, read_max_slot
from src.database.validators import read_proposed_validators
from src.database.withdrawals import insert_withdrawals_batch
from src.globals import get_config, get_logger
from src.globals.constants.config import CHAIN_START_SLOT_FIELD
from src.globals.constants.database import SLOTS_BLOCK_NUMBER_FIELD
from src.helpers.deposits import filter_deposits_batch, process_deposits_batch
from src.helpers.fee_recipient import process_fee_recipients
from src.helpers.merkle import gather_merkle_data, prepare_report
from src.helpers.portal import update_portal_pools
from src.helpers.slots import fetch_slots_batch
from src.helpers.validators import (
    should_verify_validators,
    update_portal_validators,
    verify_validators_batch,
)
from src.helpers.withdrawals import filter_withdrawals_batch, process_withdrawals_batch
from src.utils.progress_bar import progress_bar


class BeaconTrigger(Trigger):
    """
    Processes updates from both execution and consensus chains for all slots between
    the configured start slot and the latest periodically detected slot.

    The BeaconTrigger monitors slot data from the Beacon Chain, indexes relevant
    information such as deposits, withdrawals, and validators, and performs necessary
    updates and verifications. It leverages multithreading to efficiently handle
    batch operations and ensures data integrity by interacting with the database.

    Example:
        trigger = BeaconTrigger()
        daemon = SlotDaemon(trigger=trigger, slot_period=10)
        daemon.run()
        # To stop the daemon:
        # daemon.stop()

    Attributes:
        name (str): Name of the trigger used for logging and identification ("BEACON").
        __recent_slot (int): The most recently processed slot number.
    """

    name: str = "BEACON"

    def __init__(self) -> None:
        """
        Initialize a BeaconTrigger instance.

        Sets up the trigger with the `process_slots` action, which indexes and processes
        slot data on each trigger activation.

        Raises:
            ValueError: If initialization parameters are invalid.
        """

        Trigger.__init__(
            self,
            action=self.process_slots,
            name=self.name,
        )

    # pylint: disable-next=unused-argument
    def process_slots(self, curr_slot_num: int, *args: Any) -> None:
        """
        Indexes and saves all required slot data to the database, then checks for
        any subsequent actions based on the latest update.

        This method performs the following steps:
            1. Indexes slots between the last processed slot and the current slot.
                - Slots are batched in order to reduce
            2. Processes merkle calculations and validator verifications.

        Args:
            curr_slot_num (int): The current slot number being processed.
        """
        get_logger().info(f"Starting process_slots for slot number: {curr_slot_num}")

        fallback_slot = get_config(field=CHAIN_START_SLOT_FIELD)

        all_thefts: list[tuple[BigInteger, BigInteger] | None] = []
        try:
            batch_size = 1000  # TODO:(crash) should we make this a config?

            #  ceil division is needed for exact number of batches.
            batch_num = -((curr_slot_num - read_max_slot(fallback_slot) + 1) // -batch_size)
            pbar = progress_bar(
                total=batch_num,
                desc="Processing slots in batches.",
            )
            print(fallback_slot, read_max_slot(fallback_slot))
            for _ in range(batch_num):
                batch_start = read_max_slot(fallback_slot) + 1
                batch_end = min(batch_start + batch_size - 1, curr_slot_num)
                detected_thefts = self.index_slots(batch_start, batch_end)
                all_thefts.extend(detected_thefts)
                pbar.update(1)

        except Exception as e:
            get_logger().error("Failed indexing slots. ")
            raise e

        finally:
            if pbar:
                pbar.clear()  # Ensure bar is cleared
                pbar.close()  # Ensure bar is closed

        last_indexed: int = read_max_slot(fallback_slot)
        db_last_block_num = read_block_number(last_indexed)

        if all_thefts:
            # This will remove any None results, then transpose the list of tuples into a list
            # that is containing 2 list: fee_thefts & proofs
            transposed_thefts = list(map(list, zip(*list(filter(None, all_thefts)))))

            if transposed_thefts:
                # The list might be empty after filtering all the None values.
                handle_regulate_operators(
                    fee_thefts=transposed_thefts[0],
                    proofs=transposed_thefts[1],
                    block_identifier=db_last_block_num,
                )

        self.process_report_beacon(slot_number=last_indexed, block_number=db_last_block_num)
        self.process_verifications(slot_number=last_indexed, block_number=db_last_block_num)

        get_logger().info(
            f"Completed action for slot number:{curr_slot_num}. Last indexed: {last_indexed}"
        )

    # pylint: disable-next=unused-argument
    def index_slots(
        self, start_slot: int, end_slot: int
    ) -> list[tuple[BigInteger, BigInteger] | None]:
        """
        Indexes and saves all required slot data to the database.
            - do it once! (unless db is wiped out with 'geoscope reset --slots' command)
            - can restore from db in case of a restart.

        Performs the following operations:
            1. Fetches and saves new validators from portal.
            2. Processes deposits, filters according to the portal and saves.
            3. Updates constant validator data from beaconchain
            4. Processes withdrawals, filters according to the portal and saves.
            5. Updates total withdrawal amount for the validators
            6. Saves slot data to Slots table on database
            7. Processes fee recipients based on the latest slot

        Args:
            start_slot (int): The first slot number to be processed, inclusive.
            end_slot (int): The last slot number to be processed, inclusive.
        Returns:

        """

        # TODO:(later) in a case where all the slots are indexed but all other
        # tables are erased: It should start using the slots table to fill all the other info.
        # If somehow we can change the order to fetch=> save => process, then we can
        # achieve this. However, it should not do this on every trigger! So, there should be a way
        # to run this functionality once on the first run. Although processing withdrawal,
        # deposit, block fees (?) would simply require re-fetching as they are not saved to db.
        # No urgency...

        get_logger().info(f"Indexing slots from {start_slot} to {end_slot}")

        gathered_slots: list[dict] = fetch_slots_batch(first_slot=start_slot, last_slot=end_slot)
        get_logger().debug(
            f"Fetched {len(gathered_slots)} slots from {start_slot} to {end_slot}. "
            f"Missing {end_slot-start_slot-len(gathered_slots)} slots. "
        )

        # min and max are used here instead of gathered_slots[-1] or gathered_slots[0]
        # because slots can be missed by the proposers.
        first_block: int = min(
            (x for x in gathered_slots if x[SLOTS_BLOCK_NUMBER_FIELD] is not None),
            key=lambda x: x[SLOTS_BLOCK_NUMBER_FIELD],
        )[SLOTS_BLOCK_NUMBER_FIELD]

        last_block: int = max(
            (x for x in gathered_slots if x[SLOTS_BLOCK_NUMBER_FIELD] is not None),
            key=lambda x: x[SLOTS_BLOCK_NUMBER_FIELD],
        )[SLOTS_BLOCK_NUMBER_FIELD]

        update_portal_pools(block_identifier=last_block)

        update_portal_validators(
            first_block=first_block,
            last_block=last_block,
        )

        deposits: list[dict[str, str | BigInteger | int]] = filter_deposits_batch(gathered_slots)
        if deposits:
            get_logger().info(f"Processing {len(deposits)} deposits. ")
            process_deposits_batch(end_slot, deposits)
            insert_deposits_batch(deposits)

        withdrawals: list[dict[str, int | str | BigInteger]] = filter_withdrawals_batch(
            gathered_slots
        )
        if withdrawals:
            get_logger().info(f"Processing {len(withdrawals)} withdrawals")
            process_withdrawals_batch(withdrawals)
            insert_withdrawals_batch(withdrawals)

        # Since we are getting the latest processed slot here,
        # we should actually **SAVE** it at the last point where we are done
        # processing the validators, deposits and withdrawals:
        insert_slots_batch(gathered_slots)

        # After processing the changes on validators and inserting the slots
        # we will process the fee_recipients:
        detected_thefts: list[tuple[BigInteger, BigInteger] | None] = process_fee_recipients(
            start_slot
        )

        return detected_thefts

    def process_report_beacon(self, slot_number: int, block_number: int) -> None:
        """
        Gathers Merkle data and prepares a report for the Beacon Chain.

        This method performs the following steps:
            1. Reads pool IDs from the database.
            2. Gathers Merkle data for prices and balances.
            3. Prepares Merkle roots.
            4. Handles the beacon report submission
            5. If submission is successful, inserts Merkle tree JSON data into db.

        Args:
            slot_number (int): The slot number for which to process the report.
            block_number (int): The block number associated with the slot.

        """
        pool_ids: list[BigInteger] = read_pool_ids()
        if pool_ids:
            should_update, prices_data = gather_merkle_data(
                pool_ids, block_number, slot=slot_number
            )
            get_logger().debug(f"Processing report beacon for slot {slot_number},")

            try:
                if should_update and prices_data:
                    # pool[0]:pool_id pool[1]:new_price
                    prices: list[tuple[int, int]] = [
                        (int(pool[0]), pool[1]) for pool in prices_data
                    ]

                    # pool[3]:validators
                    # val[0]:pubkey
                    # val[7]:beacon_balance
                    # val[4]:withdrawn_balance
                    # val[6]:fee_recipient_balance
                    balances: list[tuple[str, int, int]] = [
                        (val[0], val[7], val[4] + val[6]) for pool in prices_data for val in pool[3]
                    ]

                    price_merkle_root: HexStr
                    balance_merkle_root: HexStr
                    price_merkle_root, balance_merkle_root, all_validators_count = prepare_report(
                        prices, balances
                    )

                    success: bool = handle_report_beacon(
                        price_merkle_root=price_merkle_root,
                        balance_merkle_root=balance_merkle_root,
                        all_validators_count=all_validators_count,
                        block_identifier=block_number,
                    )

                    if success:
                        insert_merkle_tree_json(price_merkle_root, prices)
                        insert_merkle_tree_json(balance_merkle_root, balances)
                        get_logger().info("Merkle tree JSON data saved successfully.")

                    else:
                        get_logger().error("Failed to handle beacon report.")
                else:
                    get_logger().debug("No update is required for beacon report at this time.")
            except Exception as e:
                get_logger().exception(
                    f"Error while processing beacon report for slot: {slot_number} \
                        and block: {block_number}: {e}"
                )
                raise e
        else:
            get_logger().warning("No pools detected. Beacon report is skipped... ")

    def process_verifications(self, slot_number: int, block_number: int) -> None:
        """
        Processes validator verifications based on the latest slot and block number.

        This method performs the following steps:
            1. Detects validators that need to be verified.
            2. Determines if it's the right time to verify them.
            3. Verifies the validators in batch.
            4. Updates the verification index accordingly.

        Args:
            slot_number (int): The slot number associated with the verifications.
            block_number (int): The block number associated with the verifications.
        """
        try:
            get_logger().debug(
                f"Processing verifications for slot {slot_number} and block {block_number}"
            )

            pending_validators: list[tuple[str, int, BigInteger, str, str, str, str, int]] = (
                read_proposed_validators(block_identifier=block_number)
            )

            if should_verify_validators(slot_number, pending_validators):
                get_logger().info(f"Verifying {len(pending_validators)} validators")
                aliens = verify_validators_batch(pending_validators, block_identifier=block_number)
                max_pending_validator: tuple = max(pending_validators, key=lambda x: x[1])
                new_verification_index: int = max_pending_validator[1]
                success: bool = handle_update_verification_index(
                    validator_verification_index=new_verification_index,
                    alienated_pubkeys=aliens,
                    block_identifier=block_number,
                )
                if success:
                    get_logger().info(
                        f"Verification index updated successfully to {new_verification_index}"
                    )
                else:
                    get_logger().error("Failed to update verification index.")

            else:
                get_logger().debug("No validators need verification at this time.")

        except Exception as e:
            get_logger().exception(f"Unexpected error during verification processing: {e}")
            raise e
