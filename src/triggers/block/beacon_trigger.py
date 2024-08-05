# -*- coding: utf-8 -*-

from geodefi import Geode

from src.classes import Trigger
from src.globals import get_logger, get_sdk, get_config
from src.database.validators import (
    create_validators_table,
    check_pk_in_db,
    save_beacon_balances,
    fetch_active_vals,
)
from src.database.events import (
    create_deposits_table,
    insert_deposit,
    create_info_table,
    fetch_processed_slot,
    save_processed_slot,
)

from src.utils.thread import multithread


class BeaconTrigger(Trigger):
    """Checks for beacon chain updates and processes validator balances.

    Attributes:
        name (str): name of the trigger to be used when logging etc. (value: BEACON)
    """

    name: str = "BEACON"

    def __init__(self) -> None:
        """Initializes a BeaconTrigger object. The trigger will process the changes of the daemon after a loop.
        It is a callable object. It is used to process the changes of the daemon. It can only have 1 action.
        """

        Trigger.__init__(self, name=self.name, action=self.update_beacon)
        create_validators_table()
        create_deposits_table()
        create_info_table()
        # create_withdrawals_table()
        get_logger().debug(f"{self.name} is initiated.")

    def update_beacon(self) -> None:
        """Processes the deposits and withdrawals of the beacon chain."""

        sdk: Geode = get_sdk()

        last_processed_slot = fetch_processed_slot()
        if last_processed_slot == -1:
            # start from the given slot - decide where to write on the config file
            last_processed_slot = get_config().start_slot
        current_slot = sdk.beacon.beacon_headers_id("finalized")["slot"]

        if last_processed_slot == current_slot:
            get_logger().info(f"Slot {current_slot} is already processed.")
            return

        data_batch = multithread(
            sdk.beacon.beacon_blocks,
            range(last_processed_slot + 1, current_slot + 1),
        )

        # for each deposit, check if the validator is already in the database as pubkey then update the deposit table
        for data in data_batch:
            slot: int = int(data["message"]["slot"])  # slot
            for deposit in data["deposits"]:
                deposit_data: dict = deposit["data"]
                pubkey: str = deposit_data["pubkey"]

                if not check_pk_in_db(pubkey):
                    continue

                # write the deposit data to the database deposit table
                insert_deposit(
                    pubkey,
                    deposit_data["withdrawal_credentials"],
                    deposit_data["amount"],
                    deposit_data["signature"],
                    slot,
                )

                # ?? update the validator's balance/status in the database
                # ?? set validator as valid by checking signature, withdrawal credentials if amount is 1 eth in total balance

            save_processed_slot(slot)

        get_logger().info("Deposit data successfully written to the database")
