# -*- coding: utf-8 -*-

from typing import Iterable
from web3.types import EventData
from web3.contract.contract import ContractEvent

from src.classes import Daemon, Trigger
from src.common import AttributeDict
from src.exceptions import EventFetchingError
from src.globals import get_sdk, get_constants, get_logger
from src.database.events import find_latest_event
from src.helpers.event import get_all_events


class EventDaemon(Daemon):
    """A type of Block Daemon that triggers every time the provided event is emitted.
    Interval is default block time (12s)
    Task returns the events as a list. If no events are emitted, returns None.

    Attributes:
        __recent_block (int): recent block number to be processed.
        name (str): name of the daemon to be used when logging etc. (value: EVENT_DAEMON)
        event (_type_): event to be checked.
        block_period (int): number of blocks to wait before running the triggers.
        block_identifier (int): block_identifier that can be set to
            'latest', 'earliest', 'pending', 'safe', 'finalized'.
    """

    name: str = "EVENT_DAEMON"

    def __init__(
        self,
        trigger: Trigger,
        event: ContractEvent,
    ) -> None:
        """Initializes a EventDaemon object. The daemon will run the trigger on every event emitted.

        Args:
            trigger (Trigger): an initialized Trigger instance.
            event (ContractEvent): event to be checked.
            start_block (int, optional): block number to start checking for events.
                Default is what is set in the config.
        """
        chain = get_constants().chain
        Daemon.__init__(
            self,
            interval=int(chain.interval),
            task=self.listen_events,
            trigger=trigger,
        )
        self.event = event

        # block_identifier sets if we are looking for:
        # 'latest', 'earliest', 'pending', 'safe', 'finalized'.
        self.block_identifier: str = chain.identifier
        self.block_period: int = int(chain.period)

        self.__last_snapshot: AttributeDict = find_latest_event(event.event_name)
        get_logger().debug(f"{trigger.name} is attached to an Event Daemon")

    def filter_known_events(self, e: EventData) -> bool:
        """Filter events that are in the previous block, which are not processed."""
        # TODO: (later) it might be useful to not check the events once any is found
        if int(e.blockNumber) > self.__last_snapshot.block_number:
            return True
        if int(e.transactionIndex) > self.__last_snapshot.transaction_index:
            return True
        if int(e.logIndex) > self.__last_snapshot.log_index:
            return True
        return False

    def listen_events(self) -> Iterable[EventData]:
        """The main task for the EventDaemon. Checks for new events.
        If any, activates the trigger and returns the events.
        If no events are emitted, returns None.

        Returns:
            list[dict]: list of events as dictionaries.
        """

        # eth.block_number or eth.get_block_number() can also be used
        # but this allows block_identifier.
        curr_block: int = (get_sdk().w3.eth.get_block(self.block_identifier)).number
        get_logger().debug(f"Processing Block: {curr_block}")

        # check if required number of blocks have past:
        if curr_block >= self.__last_snapshot.block_number + self.block_period:
            unknown_events = []

            try:
                detected_events: Iterable[EventData] = get_all_events(
                    event=self.event,
                    first_block=self.__last_snapshot.block_number,
                    last_block=curr_block,
                )

                # take a snapshot from db before filtering (potentially) new events.
                self.__last_snapshot: int = find_latest_event(self.event.event_name)
                unknown_events: list[EventData] = list(
                    filter(
                        self.filter_known_events,
                        detected_events,
                    )
                )

            except Exception as e:
                raise EventFetchingError(
                    "There was an issue while fetching the"
                    f"{self.event.event_name} event from the chain"
                ) from e

            # take a snapshot after finishing processing the block.\
            # Does not matter if there are events or not.
            self.__last_snapshot = AttributeDict.convert_recursive(
                {"block_number": curr_block, "transaction_index": 0, "log_index": 0}
            )

            if unknown_events:
                get_logger().debug(
                    f"{self.trigger.name} will be triggered with {len(unknown_events)} events"
                )
                return unknown_events

        else:
            get_logger().debug(
                f"Block period have not been met yet.\
                Expected block:{self.__last_snapshot.block_number + self.block_period}"
            )
