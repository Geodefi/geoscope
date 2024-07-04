# -*- coding: utf-8 -*-

from src.classes import Database
from src.globals import chain
from src.logger import log
from src.exceptions import DatabaseError
from src.common import AttributeDict


def find_latest_event(event_name: str) -> AttributeDict:
    """Finds the latest eventt info for the given event_name in the database.

    Args:
        event_name (str): Name of the event.

    Returns:
        AttributeDict: Blocknumber, tx index and log index \
            that will define the starting point for the given event_name. \
                If no event is found in database, returns provided default start info.
    """

    try:
        with Database() as db:
            db.execute(
                f"""
                SELECT block_number,transaction_index,log_index
                FROM {event_name}
                ORDER BY block_number DESC, transaction_index DESC, log_index DESC
                LIMIT 1
                """,
            )
            found_event = db.fetchone()
            if found_event:
                e = found_event
                log.debug(
                    f"Found on database:{event_name} => {e[0]}/{e[1]}/{e[2]}"
                )
                return AttributeDict.convert_recursive(
                    {
                        "block_number": e[0],
                        "transaction_index": e[1],
                        "log_index": e[2],
                    }
                )

    except Exception as e:
        raise DatabaseError(
            f"Error finding latest block for {event_name}"
        ) from e

    log.debug(
        f"Could not find the event:{event_name} on database. \
            Proceeding with default initial block:{chain.start}"
    )
    return AttributeDict.convert_recursive(
        {
            "block_number": int(chain.start),
            "transaction_index": 0,
            "log_index": 0,
        }
    )


def create_stake_proposal_table() -> None:
    """Creates the sql database table for StakeProposal.

    Raises:
        DatabaseError: Error creating StakeProposal table
    """

    try:
        with Database() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS StakeProposal (
                    pk TEXT NOT NULL PRIMARY KEY,
                    pool_id TEXT NOT NULL,
                    operator_id TEXT NOT NULL,
                    block_number INTEGER NOT NULL,
                    transaction_index INTEGER NOT NULL,
                    log_index INTEGER NOT NULL,
                )
                """
            )
        log.debug(f"Created a new table: StakeProposal")
    except Exception as e:
        raise DatabaseError("Error creating StakeProposal table") from e


def drop_stake_proposal_table() -> None:
    """Removes StakeProposal table from the database.

    Raises:
        DatabaseError: Error dropping StakeProposal table
    """

    try:
        with Database() as db:
            db.execute("""DROP TABLE IF EXISTS StakeProposal""")
        log.debug(f"Dropped Table: StakeProposal")
    except Exception as e:
        raise DatabaseError(f"Error dropping StakeProposal table") from e


def reinitialize_stake_proposal_table() -> None:
    """Removes StakeProposal table and creates an empty one."""

    drop_stake_proposal_table()
    create_stake_proposal_table()
