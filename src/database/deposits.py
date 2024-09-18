# -*- coding: utf-8 -*-
from src.classes import Database
from src.exceptions.classes.database import DatabaseError
from src.globals import get_logger


def create_deposits_table() -> None:
    """Creates the sql database table for Deposits.

    Raises:
        DatabaseError: Error creating Deposits table
    """
    try:
        with Database() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS Deposits (
                    pubkey TEXT NOT NULL PRIMARY KEY,
                    withdrawal_credentials TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    signature TEXT NOT NULL, => not needed
                    slot INTEGER NOT NULL
                )
                """
            )
        get_logger().debug(f"Created a new table: Deposits")
    except Exception as e:
        raise DatabaseError("Error creating Deposits table") from e


def drop_deposits_table() -> None:
    """Removes Deposits table from the database.

    Raises:
        DatabaseError: Error dropping Deposits table
    """

    try:
        with Database() as db:
            db.execute("""DROP TABLE IF EXISTS Deposits""")
        get_logger().debug(f"Dropped Table: Deposits")
    except Exception as e:
        raise DatabaseError(f"Error dropping Deposits table") from e


def reinitialize_deposits_table() -> None:
    """Removes Deposits table and creates an empty one."""

    drop_deposits_table()
    create_deposits_table()


def insert_many_deposits(deposits: list[dict]) -> None:
    """

    Args:
        deposits (list[dict]):

    Raises:
        DatabaseError: Error inserting many deposits into table
    """
    try:
        with Database() as db:
            db.executemany(
                "INSERT INTO Deposits VALUES (?,?,?,?,?)",
                [
                    (
                        a["pubkey"],
                        a["withdrawal_credentials"],
                        a["amount"],
                        a["signature"],
                        a["slot"],
                    )
                    for a in deposits
                ],
            )
    except Exception as e:
        raise DatabaseError(f"Error inserting many deposits into table Deposits") from e


def check_deposit_by_slot(slot: int) -> bool:
    """Checks if there are any deposits saved on the database for given slot.
    It effectively proves all deposits are processed and saved within the slot.

    Args:
        slot (int): slot to be checked for availabity

    Returns:
        bool: True if exists
    """
    try:
        with Database() as db:
            db.execute("SELECT * FROM Deposits WHERE slot = ?", (slot,))
            return db.fetchone() is not None
    except Exception as e:
        raise DatabaseError(f"Error checking if slot {slot} is in table Deposits") from e
