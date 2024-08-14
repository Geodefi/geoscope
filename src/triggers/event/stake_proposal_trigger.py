# -*- coding: utf-8 -*-


from typing import Iterable
from web3.types import EventData
from geodefi.globals.beacon import DEPOSIT_SIZE

from src.classes import Trigger, Database
from src.daemons import TimeDaemon
from src.triggers.time import ExpectPubkeysTrigger
from src.exceptions import DatabaseError
from src.globals import get_config, get_logger, get_constants
from src.helpers.event import event_handler


class StakeProposalTrigger(Trigger):
    """Triggered when a new validator is proposed. Creates validators on db.

    Attributes:
        name (str): name of the trigger to be used when logging etc. (value: STAKE_PROPOSAL)
        expect_pubkeys_daemon (str): A time daemon that will work every 15 min.\
            Checks if there are any pubkeys that requires pinging.
    """

    name: str = "STAKE_PROPOSAL"

    def __init__(self) -> None:
        """Initializes a StakeProposalTrigger object.
        The trigger will process the changes of the daemon after a loop.
        It is a callable object.
        It is used to process the changes of the daemon.
        It can only have 1 action.
        """
        Trigger.__init__(self, name=self.name, action=self.expect_validators)

        # initiate a TimeDaemon to keep track
        self.__except_pubkeys_trigger: ExpectPubkeysTrigger = ExpectPubkeysTrigger(
            balance=DEPOSIT_SIZE.PROPOSAL, keep_alive=True
        )
        self.__except_pubkeys_daemon: TimeDaemon = TimeDaemon(
            interval=15 * get_constants().one_minute,
            trigger=self.__except_pubkeys_trigger,
            initial_delay=0,
        )

        self.__except_pubkeys_daemon.run()

    def __filter_events(self, event: EventData) -> bool:
        """Filters the events to check if the event is for the script's OPERATOR_ID.

        Args:
            event (EventData): Event to be checked

        Returns:
            bool: True if the event is for the script's OPERATOR_ID, False otherwise
        """

        return event.args.operatorId == get_config().operator_id

    def __parse_events(self, events: Iterable[EventData]) -> list[tuple]:
        """Parses the events to saveable format.
        Returns a list of tuples.
        Each tuple represents a saveable event.

        Args:
            events (Iterable[EventData]): list of StakeProposal emits

        Returns:
            list[tuple]: list of saveable events
        """
        saveable_events: list[tuple] = []
        for event in events:
            for event_index, pubkey in event.args.pubkeys:
                saveable_events.append(
                    (
                        str(pubkey),
                        str(event.args.poolId),
                        event.blockNumber,
                        event.transactionIndex,
                        event.logIndex,
                        event_index,
                    )
                )

        return saveable_events

    def __save_events(self, events: list[tuple]) -> None:
        """Saves the parsed events to the database.

        Args:
            events (list[tuple]): list of distinct pubkeys coming from StakeProposal emits
        """
        try:
            with Database() as db:
                db.executemany(
                    "INSERT INTO StakeProposal VALUES(?,?,?,?,?,?)",
                    events,
                )
            get_logger().debug(f"Inserted {len(events)} events into StakeProposal table")
        except Exception as e:
            raise DatabaseError(f"Error inserting events to table StakeProposal") from e

    # pylint: disable-next=unused-argument
    def expect_validators(self, events: Iterable[EventData], *args, **kwargs) -> None:
        """Creates a new pool and fills it with data
        for encountered pool ids within provided "StakeProposal" emits.

        Args:
            events (Iterable[EventData]): list of events
        """

        filtered_events: Iterable[EventData] = event_handler(
            events,
            self.__parse_events,
            self.__save_events,
            self.__filter_events,
        )

        # gather all distinct pubkeys from filtered events' pubkeys list, then flatten
        all_proposed_pks: list[list[str]] = [
            pubkey for event in filtered_events for pubkey in event.args.pubkeys
        ]

        self.__except_pubkeys_trigger.extend(all_proposed_pks)
