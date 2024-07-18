# -*- coding: utf-8 -*-

from typing import Iterable
from web3.types import EventData

from src.classes import Trigger, Database
from src.database.validators import (
    create_validators_table,
    fill_validators_table,
)
from src.database.events import create_stake_proposal_table
from src.helpers.event import event_handler
from src.exceptions.classes.database import DatabaseError
from src.globals import get_logger


class StakeProposalTrigger(Trigger):
    """Triggered when validators are proposed.
    Updates the database with the latest info.

    Attributes:
        name (str): name of the trigger to be used when logging etc. (value: STAKE_PROPOSAL)
    """

    name: str = "STAKE_PROPOSAL"

    def __init__(self) -> None:
        """Initializes a StakeProposalTrigger object. The trigger will process the changes of the daemon after a loop.
        It is a callable object. It is used to process the changes of the daemon. It can only have 1 action.
        """

        Trigger.__init__(self, name=self.name, action=self.consider_deposit)
        create_validators_table()
        create_stake_proposal_table()
        get_logger().debug(f"{self.name} is initated.")

    def __parse_events(self, events: Iterable[EventData]) -> list[tuple]:
        """Parses the events to saveable format. Returns a list of tuples. Each tuple represents a saveable event.

        Args:
            events (Iterable[EventData]): list of StakeProposal emits

        Returns:
            list[tuple]: list of saveable events
        """

        saveable_events: list[tuple] = []
        for event in events:
            for pubkey in event.args.pubkeys:
                saveable_events.append(
                    (
                        pubkey,
                        str(event.args.poolId),
                        str(event.args.operatorId),
                        event.blockNumber,
                        event.transactionIndex,
                        event.logIndex,
                    )
                )

        return saveable_events

    def __save_events(self, events: list[tuple]) -> None:
        """Saves the events to the database.

        Args:
            events (list[tuple]): list of StakeProposal emits
        """
        try:
            with Database() as db:
                db.executemany(
                    "INSERT INTO StakeProposal VALUES (?,?,?,?,?,?)",
                    events,
                )
            get_logger().debug(
                f"Inserted {len(events)} events into StakeProposal table"
            )
        except Exception as e:
            raise DatabaseError(
                f"Error inserting events to table StakeProposal"
            ) from e

    def consider_deposit(
        self, events: Iterable[EventData], *args, **kwargs
    ) -> None:
        """Updates the validators table with the latest info.

        Args:
            events (Iterable[EventData]): list of events
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        get_logger().info(f"{self.name} is triggered.")

        # parse and save events
        filtered_events: Iterable[EventData] = event_handler(
            events, self.__parse_events, self.__save_events
        )

        pks: list[str] = list()
        for event in filtered_events:
            pks.extend(event.args.pubkeys)

        # TODO: update fill_validators_table if needed more parameters to be added to the validators table
        fill_validators_table(pks)
