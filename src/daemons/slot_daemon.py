# -*- coding: utf-8 -*-

from src.classes import Daemon, Trigger
from src.globals import get_sdk, get_logger, get_constants


class SlotDaemon(Daemon):
    """A Daemon that triggers provided actions on every X slot on the beaconchain.
    Interval is default slot time (12s)
    Task returns: last slot number which activates the triggers.

    Attributes:
        __recent_slot (int): recent slot number to be processed.
        name (str): name of the daemon to be used when logging etc. (value: SLOT_DAEMON)
        slot_period (int): number of slots to wait before running the triggers.
        slot_identifier (int): "head" (canonical head in node's view), "genesis", "finalized", \
            <slot>, <hex encoded blockRoot with 0x prefix>
    """

    name: str = "SLOT_DAEMON"

    def __init__(
        self,
        trigger: Trigger,
        slot_period: int,
    ) -> None:
        """Initializes a SlotDaemon object. The daemon will run the triggers on every X slot.

        Args:
            trigger (Trigger): an initialized Trigger instance.
            slot_period (int, optional): number of slots to wait before \
                running the triggers. Default is what is set in the config.
        """
        chain = get_constants().chain
        Daemon.__init__(
            self,
            interval=int(chain.interval),
            task=self.listen_slots,
            trigger=trigger,
        )

        self.slot_identifier: int = chain.identifier
        self.__recent_slot: int = chain.start.slot
        self.slot_period: int = slot_period
        get_logger().debug(f"{trigger.name} is attached to a Slot Daemon")

    def listen_slots(self) -> int:
        """Evaluates the appropriate slot, according to slot_identifier returns if period is achieved.

        Returns:
            int: the latest processed slot number.
        """
        try:
            curr_slot: dict = get_sdk().beacon.beacon_blocks(self.slot_identifier)
            curr_slot_msg: dict = curr_slot["message"]
            curr_slot_num: int = int(curr_slot_msg["slot"])
            get_logger().debug(f"Slot detected: {curr_slot_num}")

            # check if the new slot number aligns with the required period:
            # this is important to align all oracle instances
            if (curr_slot_num - self.__recent_slot) % self.slot_period == 0:
                self.__recent_slot = curr_slot_num
                return curr_slot_num

            get_logger().debug(f"Slot period have not been met yet.")
            return None

        except Exception:
            get_logger().debug(f"Slot was missed by the proposer.")
            return None
