# -*- coding: utf-8 -*-

from src.classes import Database
from src.common import AttributeDict
from src.globals.constants import chain
from src.exceptions.classes.database import DatabaseError
from src.globals import get_logger


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
                get_logger().debug(
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

    get_logger().debug(
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


def create_info_table() -> None:
    """Creates the sql database table for Info.

    Raises:
        DatabaseError: Error creating Info table
    """

    try:
        with Database() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS Info (
                    processed_slot INTEGER
                )
                """
            )
        get_logger().debug(f"Created a new table: Info")
    except Exception as e:
        raise DatabaseError("Error creating Info table") from e


def drop_info_table() -> None:
    """Removes Info table from the database.

    Raises:
        DatabaseError: Error dropping Info table
    """

    try:
        with Database() as db:
            db.execute("""DROP TABLE IF EXISTS Info""")
        get_logger().debug(f"Dropped Table: Info")
    except Exception as e:
        raise DatabaseError(f"Error dropping Info table") from e


def reinitialize_info_table() -> None:
    """Removes Info table and creates an empty one."""

    drop_info_table()
    create_info_table()


def fetch_processed_slot() -> int:
    """Fetches the processed slot from the database.

    Returns:
        int: Processed slot number
    """

    try:
        with Database() as db:
            db.execute(
                """
                SELECT processed_slot
                FROM Info
                """,
            )
            processed_slot = db.fetchone()
            if processed_slot:
                return processed_slot[0]
            return -1
    except Exception as e:
        raise DatabaseError("Error fetching processed slot") from e


def save_processed_slot(slot: int) -> None:
    """Saves the processed slot to the database.

    Args:
        slot (int): Slot number to be saved
    """

    try:
        with Database() as db:
            db.execute(
                """
                UPDATE Info
                SET processed_slot = ?
                """,
                (slot,),
            )
        get_logger().info(f"Saved processed slot to database: {slot}")
    except Exception as e:
        raise DatabaseError("Error saving processed slot") from e


def insert_processed_slot(slot: int) -> None:
    """Inserts the processed slot to the database.

    Args:
        slot (int): Slot number to be inserted
    """

    try:
        with Database() as db:
            db.execute(
                """
                INSERT INTO Info VALUES (?)
                """,
                (slot,),
            )
        get_logger().debug(f"Inserted processed slot to database: {slot}")
    except Exception as e:
        raise DatabaseError("Error inserting processed slot") from e


# TODO: deposits and withdrawals are not actually events like info table
def create_deposits_table() -> None:
    """Creates the sql database table for Deposit.

    Raises:
        DatabaseError: Error creating Deposit table
    """

    try:
        with Database() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS Deposit (
                    pubkey TEXT NOT NULL PRIMARY KEY,
                    withdrawal_credentials TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    slot INTEGER NOT NULL
                )
                """
            )
        get_logger().debug(f"Created a new table: Deposit")
    except Exception as e:
        raise DatabaseError("Error creating Deposit table") from e


def drop_deposits_table() -> None:
    """Removes Deposit table from the database.

    Raises:
        DatabaseError: Error dropping Deposit table
    """

    try:
        with Database() as db:
            db.execute("""DROP TABLE IF EXISTS Deposit""")
        get_logger().debug(f"Dropped Table: Deposit")
    except Exception as e:
        raise DatabaseError(f"Error dropping Deposit table") from e


def reinitialize_deposit_table() -> None:
    """Removes Deposit table and creates an empty one."""

    drop_deposits_table()
    create_deposits_table()


def insert_deposit(
    pubkey: str,
    withdrawal_credentials: str,
    amount: str,
    signature: str,
    slot: int,
) -> None:
    """Inserts a new deposit to the database.

    Args:
        pubkey (str): Public key of the validator
        withdrawal_credentials (str): Withdrawal credentials of the validator
        amount (str): Amount of the deposit
        signature (str): Signature of the deposit
        slot (int): block number of the deposit
    """

    try:
        with Database() as db:
            db.execute(
                """
                INSERT INTO Deposit VALUES (?,?,?,?,?)
                """,
                (pubkey, withdrawal_credentials, amount, signature, slot),
            )
        get_logger().debug(f"Inserted a new deposit to the database")
    except Exception as e:
        raise DatabaseError("Error inserting deposit to table Deposit") from e


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
        get_logger().debug(f"Created a new table: StakeProposal")
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
        get_logger().debug(f"Dropped Table: StakeProposal")
    except Exception as e:
        raise DatabaseError(f"Error dropping StakeProposal table") from e


def reinitialize_stake_proposal_table() -> None:
    """Removes StakeProposal table and creates an empty one."""

    drop_stake_proposal_table()
    create_stake_proposal_table()
