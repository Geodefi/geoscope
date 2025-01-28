"""
Functions to manage the Deposits table in the database.
"""

from src.classes import Database
from src.common import BigInteger
from src.database.utils.generators import (
    generate_create_table_sql,
    generate_drop_table_sql,
    generate_insert_sql,
    generate_select_exists_sql,
)
from src.exceptions.classes.database import DatabaseError
from src.globals import get_logger
from src.globals.constants.database import DEPOSITS_SLOT_FIELD, DEPOSITS_TABLE_KEY

# Pre-rendered SQL Statements
CREATE_TABLE_SQL: str = generate_create_table_sql(DEPOSITS_TABLE_KEY)
DROP_TABLE_SQL: str = generate_drop_table_sql(DEPOSITS_TABLE_KEY)
INSERT_SQL: str = generate_insert_sql(DEPOSITS_TABLE_KEY)
CHECK_SLOT_EXISTS_SQL: str = generate_select_exists_sql(DEPOSITS_TABLE_KEY, DEPOSITS_SLOT_FIELD)


def create_deposits_table() -> None:
    """Creates the sql database table for Deposits.
    Raises:
        DatabaseError: Error creating Deposits table
    """
    try:
        with Database() as db:
            db.execute(CREATE_TABLE_SQL)
        get_logger().debug(f"Created a new table: {DEPOSITS_TABLE_KEY}")
    except Exception as e:
        raise DatabaseError(f"Error creating {DEPOSITS_TABLE_KEY} table") from e


def drop_deposits_table() -> None:
    """Removes Deposits table from the database.

    Raises:
        DatabaseError: Error dropping Deposits table
    """

    try:
        with Database() as db:
            db.execute(DROP_TABLE_SQL)
        get_logger().debug(f"Dropped Table: {DEPOSITS_TABLE_KEY}")
    except Exception as e:
        raise DatabaseError(f"Error dropping {DEPOSITS_TABLE_KEY} table") from e


def reinitialize_deposits_table() -> None:
    """Removes Deposits table and creates an empty one."""
    try:
        with Database() as db:
            db.execute(DROP_TABLE_SQL)
            db.execute(CREATE_TABLE_SQL)
        get_logger().warning(f"Reinitialized table: {DEPOSITS_TABLE_KEY}")
    except DatabaseError as e:
        get_logger().error(f"Failed to reinitialize {DEPOSITS_TABLE_KEY} table.")
        raise e


def insert_deposits_batch(deposits: list[dict[str, str | int | BigInteger]]) -> None:
    """
    Insert a batch of deposit records into the Deposits table.

     Args:
        deposits (list[dict]):
            Each deposit in the list represented as a dictionary with the following keys:
            - DEPOSITS_PUBKEY_FIELD (str): The public key of the validator.
            - DEPOSITS_SIGNATURE_FIELD (str): The signature of the deposit data.
            - DEPOSITS_AMOUNT_FIELD (BigInteger): The amount deposited.
            - DEPOSITS_SLOT_FIELD (int): The slot number when the deposit was made.
            - DEPOSITS_WITHDRAWAL_CREDENTIALS_FIELD (str): Credentials for withdrawal.

    Raises:
        DatabaseError: If insertion into the database fails.
    """
    try:
        with Database() as db:
            db.executemany(INSERT_SQL, deposits)
        get_logger().debug(f"Inserted {len(deposits)} new deposits into {DEPOSITS_TABLE_KEY} table")
    except Exception as e:
        raise DatabaseError(f"Error inserting deposits into table {DEPOSITS_TABLE_KEY}") from e


def check_deposit_by_slot(slot: int) -> bool:
    """
    Checks if there are any deposits saved in the database for the given slot.

    There can be multiple deposits in one slot. Finding any deposit for the slot
    indicates that deposits for that slot have been processed and saved.

    Args:
        slot (int): The slot number to check for deposits.

    Returns:
        bool: True if at least one deposit exists for the slot, False otherwise.

    Raises:
        DatabaseError: If there is an error querying the database.
    """
    try:

        with Database() as db:
            db.execute(CHECK_SLOT_EXISTS_SQL, {DEPOSITS_SLOT_FIELD: slot})
            return db.fetchone() is not None
    except Exception as e:
        raise DatabaseError(
            f"Error checking if slot {slot} is in table {DEPOSITS_TABLE_KEY}"
        ) from e
