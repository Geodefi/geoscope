"""
Defines the SlotDaemon class, a daemon for executing actions based on Beacon Chain slot intervals.

SlotDaemon monitors Beacon Chain slots and triggers specified actions when slot period is reached,
enabling automated responses to slot-based events.

Classes:
    SlotDaemon: Executes actions at intervals defined by Beacon Chain slot numbers.
"""

from typing import Any

from src.classes import Daemon, Trigger
from src.database.slots import read_max_slot
from src.globals import get_config, get_logger, get_sdk
from src.globals.constants.config import (
    CHAIN_IDENTIFIER_FIELD,
    CHAIN_INTERVAL_FIELD,
    CHAIN_START_SLOT_FIELD,
)


class SlotDaemon(Daemon):
    """
    A Daemon that triggers provided actions on every X slot on the Beacon Chain.

    The SlotDaemon monitors slots on the Beacon Chain and executes associated triggers
    when the specified slot period is achieved. By default, the interval aligns with
    the typical slot time (12 seconds).

    Example:
        def on_new_slot(slot_number: int):
            print(f"New slot processed: {slot_number}")

        trigger = Trigger(action=on_new_slot, name="NewSlotTrigger")
        slot_daemon = SlotDaemon(trigger=trigger, slot_period=10)
        slot_daemon.run()
        # To stop the daemon:
        # slot_daemon.stop()

    Attributes:
        __recent_slot (int): The most recently processed slot number.
        name (str): The name of the daemon used for logging purposes ("SLOT_DAEMON").
        slot_period (int): Number of slots to wait before executing triggers.
        slot_identifier (str): Identifier for fetching slots (e.g., "head", "genesis").
    """

    name: str = "SLOT_DAEMON"

    def __init__(
        self,
        trigger: Trigger,
        slot_period: int,
    ) -> None:
        """
        Initialize a SlotDaemon instance.

        The daemon will monitor slots on the Beacon Chain and execute triggers
        when the specified slot period is reached.

        Args:
            trigger (Trigger): An initialized Trigger instance to be executed.
            slot_period (int): Number of slots to wait before running the triggers.

        Raises:
            ValueError: If slot_period is not a positive integer.
        """
        if not isinstance(slot_period, int) or slot_period <= 0:
            raise ValueError("slot_period must be a positive integer.")

        super().__init__(
            interval=get_config(field=CHAIN_INTERVAL_FIELD),
            task=self.listen_slots,
            trigger=trigger,
        )

        self.slot_identifier: str = get_config(field=CHAIN_IDENTIFIER_FIELD)
        self.__recent_slot: int = read_max_slot(
            fallback_slot=get_config(field=CHAIN_START_SLOT_FIELD)
        )

        self.slot_period: int = slot_period
        get_logger().debug(f"Trigger '{trigger:^20}' is attached to {self.name:^20}.")

    def listen_slots(self) -> int | None:
        """
        Monitor the current slot and determine if triggers should be activated.

        This method fetches the latest slot information from the Beacon Chain.
        If the difference between the current slot and the recent slot meets the
        specified slot_period, it updates the recent_slot and activates the triggers.

        Returns:
            int | None: The latest processed slot number if the slot_period is met; otherwise, None.
        """
        try:
            curr_slot: Any = get_sdk().beacon.beacon_blocks(self.slot_identifier)
            curr_slot_msg: dict = curr_slot["message"]
            curr_slot_num: int = int(curr_slot_msg["slot"])
            get_logger().debug(f"Slot detected: {curr_slot_num}")

            # Check if the slot period has been achieved:
            # this is important to align all oracle instances
            if (
                curr_slot_num - self.__recent_slot
            ) >= self.slot_period and curr_slot_num % self.slot_period == 0:
                # TODO:(crash) check if this logic looks ok.
                self.__recent_slot = curr_slot_num
                get_logger().info(
                    f"Slot period achieved at slot {curr_slot_num}. Triggering actions..."
                )
                return curr_slot_num

            get_logger().debug("Slot period have not been met yet.")
            return None

        # pylint: disable-next=broad-exception-caught
        except Exception:
            get_logger().debug("Slot was probably missed by the proposer. Proceeding...")
            return None
