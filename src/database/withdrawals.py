"""
Functions to manage the Withdrawals table in the database.
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
from src.globals.constants.database import WITHDRAWALS_SLOT_FIELD, WITHDRAWALS_TABLE_KEY

# Pre-rendered SQL Statements
CREATE_TABLE_SQL: str = generate_create_table_sql(WITHDRAWALS_TABLE_KEY)
DROP_TABLE_SQL: str = generate_drop_table_sql(WITHDRAWALS_TABLE_KEY)
INSERT_SQL: str = generate_insert_sql(WITHDRAWALS_TABLE_KEY)
CHECK_SLOT_EXISTS_SQL: str = generate_select_exists_sql(
    WITHDRAWALS_TABLE_KEY, WITHDRAWALS_SLOT_FIELD
)


def create_withdrawals_table() -> None:
    """Creates the sql database table for Withdrawals.
    Raises:
        DatabaseError: Error creating Withdrawals table
    """
    try:
        with Database() as db:
            db.execute(CREATE_TABLE_SQL)
        get_logger().debug(f"Created a new table: {WITHDRAWALS_TABLE_KEY}")
    except Exception as e:
        raise DatabaseError(f"Error creating {WITHDRAWALS_TABLE_KEY} table") from e


def drop_withdrawals_table() -> None:
    """Removes Withdrawals table from the database.

    Raises:
        DatabaseError: Error dropping Withdrawals table
    """

    try:
        with Database() as db:
            db.execute(DROP_TABLE_SQL)
        get_logger().debug(f"Dropped Table: {WITHDRAWALS_TABLE_KEY}")
    except Exception as e:
        raise DatabaseError(f"Error dropping {WITHDRAWALS_TABLE_KEY} table") from e


def reinitialize_withdrawals_table() -> None:
    """Removes Withdrawals table and creates an empty one."""
    try:
        with Database() as db:
            db.execute(DROP_TABLE_SQL)
            db.execute(CREATE_TABLE_SQL)
        get_logger().warning(f"Reinitialized table: {WITHDRAWALS_TABLE_KEY}")
    except DatabaseError as e:
        get_logger().error(f"Failed to reinitialize {WITHDRAWALS_TABLE_KEY} table.")
        raise e


def insert_withdrawals_batch(withdrawals: list[dict[str, str | int | BigInteger]]) -> None:
    """
    Insert a batch of withdrawal records into the Withdrawals table.

    Args:
        withdrawals (list[dict[str, str | int | BigInteger]]):
            Each withdrawal in the list represented as a dictionary with the following keys:
            - WITHDRAWALS_VALIDATOR_INDEX_FIELD (int): The Beacon chain index of the validator.
            - WITHDRAWALS_ADDRESS_FIELD (str): The recipient address of the withdrawal.
            - WITHDRAWALS_AMOUNT_FIELD (BigInteger): The amount withdrawn.
            - WITHDRAWALS_SLOT_FIELD (int): The slot number when the withdrawal was made.

    Raises:
        DatabaseError: If insertion into the database fails.
    """
    try:
        with Database() as db:
            db.executemany(INSERT_SQL, withdrawals)
        get_logger().debug(
            f"Inserted {len(withdrawals)} new withdrawals into {WITHDRAWALS_TABLE_KEY} table"
        )
    except Exception as e:
        raise DatabaseError(
            f"Error inserting withdrawals into table {WITHDRAWALS_TABLE_KEY}"
        ) from e


def check_withdrawal_by_slot(slot: int) -> bool:
    """
    Checks if there are any withdrawals saved in the database for the given slot.

    There can be multiple withdrawals in one slot. Finding any withdrawals for the slot
    indicates that withdrawals for that slot have been processed and saved.

    Args:
        slot (int): The slot number to check for withdrawals.

    Returns:
        bool: True if at least one withdrawals exists for the slot, False otherwise.

    Raises:
        DatabaseError: If there is an error querying the database.
    """
    try:
        with Database() as db:
            db.execute(CHECK_SLOT_EXISTS_SQL, {WITHDRAWALS_SLOT_FIELD: slot})
            return db.fetchone() is not None
    except Exception as e:
        raise DatabaseError(
            f"Error checking if slot {slot} is in table {WITHDRAWALS_SLOT_FIELD}"
        ) from e
