# -*- coding: utf-8 -*-
from src.classes import Database
from src.exceptions.classes.database import DatabaseError
from src.globals import get_logger


def create_withdrawals_table() -> None:
    """Creates the sql database table for Withdrawals.

    Raises:
        DatabaseError: Error creating Withdrawals table
    """

    try:
        with Database() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS Withdrawals (
                    index INTEGER NOT NULL UNIQUE,
                    validator_index INTEGER NOT NULL PRIMARY KEY,
                    address TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    slot INTEGER NOT NULL
                )
                """
            )
        get_logger().debug(f"Created a new table: Withdrawals")
    except Exception as e:
        raise DatabaseError("Error creating Withdrawals table") from e


def drop_withdrawals_table() -> None:
    """Removes Withdrawals table from the database.

    Raises:
        DatabaseError: Error dropping Withdrawals table
    """

    try:
        with Database() as db:
            db.execute("""DROP TABLE IF EXISTS Withdrawals""")
        get_logger().debug(f"Dropped Table: Withdrawals")
    except Exception as e:
        raise DatabaseError(f"Error dropping Withdrawals table") from e


def reinitialize_withdrawals_table() -> None:
    """Removes Withdrawals table and creates an empty one."""

    drop_withdrawals_table()
    create_withdrawals_table()


def insert_many_withdrawals(withdrawals: list[dict]) -> None:
    """

    Args:
        withdrawals (list[dict]):

    Raises:
        DatabaseError: Error inserting many withdrawals into table
    """

    try:
        with Database() as db:
            db.executemany(
                """
                INSERT INTO Withdrawals VALUES (
                    :index
                    :validator_index
                    :address
                    :amount
                    :slot
                )
                """,
                withdrawals,
            )
    except Exception as e:
        raise DatabaseError(f"Error inserting many withdrawals into table Withdrawals") from e


def check_withdrawal_by_slot(slot: int) -> bool:
    """Checks if there are any withdrawals saved on the database for given slot.
    There can be many withdrawals in one slot. Determining just one 'saved' deposit
    effectively proves all withdrawals are processed and saved for the given slot.


    Args:
        slot (int): slot to be checked for availabity

    Returns:
        bool: True if exists
    """
    try:
        with Database() as db:
            db.execute("SELECT * FROM Withdrawals WHERE slot = ?", (slot,))
            return db.fetchone() is not None
    except Exception as e:
        raise DatabaseError(f"Error checking if slot {slot} is in table Withdrawals") from e
