# -*- coding: utf-8 -*-

from src.classes import Database
from src.exceptions.classes.database import DatabaseError, DatabaseMismatchError
from src.globals import get_logger, get_constants


def create_slots_table() -> None:
    """Creates the sql database table to store the Slots info.

    Raises:
        DatabaseError: Error creating Slots table
    """

    try:
        with Database() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS Slots (
                    slot INTEGER NOT NULL PRIMARY KEY,
                    block_number INTEGER UNIQUE,
                    proposer_index INTEGER,
                    fee_recipient TEXT,
                    burned_amount TEXT,
                )
                """
            )
        get_logger().debug(f"Created a new table: Slots")
    except Exception as e:
        raise DatabaseError("Error creating Slots table") from e


def drop_slots_table() -> None:
    """Removes Slots table from the database.

    Raises:
        DatabaseError: Error dropping Slots table
    """

    try:
        with Database() as db:
            db.execute("""DROP TABLE IF EXISTS Slots""")
        get_logger().debug(f"Dropped Table: Slots")
    except Exception as e:
        raise DatabaseError(f"Error dropping Slots table") from e


def reinitialize_slots_table() -> None:
    """Removes Slots table and creates an empty one."""

    create_slots_table()
    drop_slots_table()


def insert_slots_batch(gathered_slots: list[dict]) -> None:
    """Inserts the gathered data for the given slots into the database.

    Args:
        gathered_slots (list[dict]): list of dictionaries containing the filtered info about gathered slots

    Raises:
        DatabaseError: Error inserting many slots into table
    """

    try:
        with Database() as db:
            db.executemany(
                """
                INSERT INTO Slots VALUES (
                    :slot,
                    :block_number,
                    :proposer_index,
                    :fee_recipient,
                    :burned_amount,
                )
                """,
                gathered_slots,
            )
        get_logger().debug(f"Inserted {len(gathered_slots)} new slots in Slots table")
    except Exception as e:
        raise DatabaseError(f"Error inserting many slots into table Slots") from e


def read_max_slot() -> int:
    """Returns the maximum slot number available on the Slots table"""
    try:
        fallback_slot: int = int(get_constants().chain.start.slot)
        with Database() as db:
            db.execute("SELECT COALESCE(MAX(slot), ?) FROM Slots", (fallback_slot,))
            return db.fetchone()[0]
    except Exception as e:
        raise DatabaseError(f"Error getting the max slot number from table Slots") from e


def read_block_number(slot: int) -> int:
    """Fetches the block number of given slot from the database.

    Returns:
        int: block number of given slot

    Raises:
        DatabaseMismatchError: There are more than 1 Slots with the same height.
        DatabaseError: Error fetching block_number from table Slots
    """
    try:
        with Database() as db:
            db.execute("SELECT block_number FROM Slots WHERE slot = ?", (slot,))
            result = db.fetchall()
            if result:
                if len(result) == 1:
                    return result[0][0]
                else:
                    raise DatabaseMismatchError(
                        f"There are {len(result)} slots with the same height in table Slots"
                    )
            return False
    except Exception as e:
        raise DatabaseError(f"Error fetching block_number from table Slots") from e


def filter_slots_by_proposer(slot: int) -> list[tuple]:
    """Returns the fee proposer_index, block_number, fee_recipient, burned_amount and also expected fee_recipient
    which corresponds to Validators' Pool' withdrawal_contract_address.
    for slots that are proposed by our validators.

    Args:
        slot (int): minimum slot number to be taken into the consideration.
    """
    try:
        with Database() as db:
            db.execute(
                """
                SELECT proposer_index, block_number, fee_recipient, burned_amount, Pools.withdrawal_contract_address
                FROM Slots
                INNER JOIN Validators ON Slots.proposer_index = Validators.beacon_index
                INNER JOIN Pools ON Validators.pool_id = Pools.id
                WHERE Slots.slot > ?;
                """,
                (slot,),
            )
            return db.fetchall()
    except Exception as e:
        raise DatabaseError(f"Error getting the max slot number from table Slots") from e
