"""
Functions to manage the Slots table in the database.
"""

from typing import Any

from src.classes import Database
from src.common import BigInteger
from src.database.utils.generators import (
    Condition,
    generate_create_table_sql,
    generate_drop_table_sql,
    generate_insert_sql,
    generate_select_fields_where_conditions_sql,
)
from src.database.utils.helpers import quote_identifier
from src.exceptions.classes.database import DatabaseError, DatabaseMismatchError
from src.globals import get_logger
from src.globals.constants.database import (
    POOLS_POOL_ID_FIELD,
    POOLS_TABLE_KEY,
    POOLS_WITHDRAWAL_CONTRACT_ADDRESS_FIELD,
    SLOTS_BLOCK_NUMBER_FIELD,
    SLOTS_BURNED_AMOUNT_FIELD,
    SLOTS_FEE_RECIPIENT_FIELD,
    SLOTS_PROPOSER_INDEX_FIELD,
    SLOTS_SLOT_FIELD,
    SLOTS_TABLE_KEY,
    VALIDATORS_BEACON_INDEX_FIELD,
    VALIDATORS_POOL_ID_FIELD,
    VALIDATORS_TABLE_KEY,
)

# Pre-rendered SQL Statements
CREATE_TABLE_SQL: str = generate_create_table_sql(SLOTS_TABLE_KEY)
DROP_TABLE_SQL: str = generate_drop_table_sql(SLOTS_TABLE_KEY)
INSERT_SQL: str = generate_insert_sql(SLOTS_TABLE_KEY)
SELECT_BLOCK_NUMBER_SQL: str = generate_select_fields_where_conditions_sql(
    SLOTS_TABLE_KEY,
    [Condition(field=SLOTS_SLOT_FIELD, operator="=")],
    SLOTS_BLOCK_NUMBER_FIELD,
)


SELECT_MAX_SLOT_SQL: str = f"""
    SELECT COALESCE(MAX({quote_identifier(SLOTS_SLOT_FIELD)}), ?) FROM {quote_identifier(SLOTS_TABLE_KEY)};
    """

SELECT_PROPOSER_FILTERED_SLOTS_SQL = f"""
            SELECT
                {quote_identifier(SLOTS_TABLE_KEY)}.{quote_identifier(SLOTS_PROPOSER_INDEX_FIELD)},
                {quote_identifier(SLOTS_TABLE_KEY)}.{quote_identifier(SLOTS_BLOCK_NUMBER_FIELD)},
                {quote_identifier(SLOTS_TABLE_KEY)}.{quote_identifier(SLOTS_FEE_RECIPIENT_FIELD)},
                {quote_identifier(SLOTS_TABLE_KEY)}.{quote_identifier(SLOTS_BURNED_AMOUNT_FIELD)},
                {quote_identifier(POOLS_TABLE_KEY)}.{quote_identifier(POOLS_WITHDRAWAL_CONTRACT_ADDRESS_FIELD)}
            FROM {quote_identifier(SLOTS_TABLE_KEY)}
            INNER JOIN {quote_identifier(VALIDATORS_TABLE_KEY)}
                ON {quote_identifier(SLOTS_TABLE_KEY)}.{quote_identifier(SLOTS_PROPOSER_INDEX_FIELD)} = {quote_identifier(VALIDATORS_TABLE_KEY)}.{quote_identifier(VALIDATORS_BEACON_INDEX_FIELD)}
            INNER JOIN {quote_identifier(POOLS_TABLE_KEY)}
                ON {quote_identifier(VALIDATORS_TABLE_KEY)}.{quote_identifier(VALIDATORS_POOL_ID_FIELD)} = {quote_identifier(POOLS_TABLE_KEY)}.{quote_identifier(POOLS_POOL_ID_FIELD)}
            WHERE {quote_identifier(SLOTS_TABLE_KEY)}.{quote_identifier(SLOTS_SLOT_FIELD)} > :min_slot;
        """


def create_slots_table() -> None:
    """
    Creates the Slots table in the database.

    Raises:
        DatabaseError: If there is an error creating the table.
    """
    try:
        with Database() as db:
            db.execute(CREATE_TABLE_SQL)
        get_logger().debug(f"Created table: {SLOTS_TABLE_KEY}")
    except Exception as e:
        raise DatabaseError(f"Error creating {SLOTS_TABLE_KEY} table") from e


def drop_slots_table() -> None:
    """
    Drops the Slots table from the database.

    Raises:
        DatabaseError: If there is an error dropping the table.
    """
    try:
        with Database() as db:
            db.execute(DROP_TABLE_SQL)
        get_logger().debug(f"Dropped table: {SLOTS_TABLE_KEY}")
    except Exception as e:
        raise DatabaseError(f"Error dropping {SLOTS_TABLE_KEY} table") from e


def reinitialize_slots_table() -> None:
    """
    Reinitializes the Slots table by dropping and recreating it.

    Raises:
        DatabaseError: If there is an error reinitializing the table.
    """
    try:
        with Database() as db:
            db.execute(DROP_TABLE_SQL)
            db.execute(CREATE_TABLE_SQL)
        get_logger().warning(f"Reinitialized table: {SLOTS_TABLE_KEY}")
    except Exception as e:
        get_logger().error(f"Failed to reinitialize {SLOTS_TABLE_KEY} table.")
        raise DatabaseError(f"Error reinitializing {SLOTS_TABLE_KEY} table") from e


def insert_slots_batch(gathered_slots: list[dict[str, Any]]) -> None:
    """
    Inserts multiple slot records into the Slots table.

    Args:
        gathered_slots (list[dict[str, Any]]): List of slot records to insert.
            Each record should include the following fields:
                - SLOTS_SLOT_FIELD (int): The slot number.
                - SLOTS_BLOCK_NUMBER_FIELD (int): The block number.
                - SLOTS_PROPOSER_INDEX_FIELD (int): The proposer index.
                - SLOTS_FEE_RECIPIENT_FIELD (str): The fee recipient address.
                - SLOTS_BURNED_AMOUNT_FIELD (BigInteger): The burned amount.

    Raises:
        DatabaseError: If insertion into the database fails.
    """
    try:
        with Database() as db:
            db.executemany(INSERT_SQL, gathered_slots)
        get_logger().debug(f"Inserted {len(gathered_slots)} records into {SLOTS_TABLE_KEY} table")
    except Exception as e:
        raise DatabaseError(f"Error inserting slots into table {SLOTS_TABLE_KEY}") from e


def read_block_number(slot: int) -> int:
    """
    Fetches the block number for a given slot from the database.

    Args:
        slot (int): The slot number to retrieve the block number for.

    Returns:
        int: The block number associated with the slot.

    Raises:
        DatabaseError: If there is an error querying the database.
    """
    try:
        with Database() as db:
            db.execute(SELECT_BLOCK_NUMBER_SQL, {SLOTS_SLOT_FIELD: slot})
            result = db.fetchone()

            if not result:
                raise DatabaseMismatchError(f"No block number found for slot {slot}")

            return result[0]
    except Exception as e:
        raise DatabaseError(
            f"Error fetching block number for slot {slot} from table {SLOTS_TABLE_KEY}"
        ) from e


def read_max_slot(fallback_slot: int) -> int:
    """
    Returns the maximum slot number available in the Slots table.

    If the Slots table is empty, it returns the fallback slot number from the constants.

    Args:
        fallback_slot (int): Fallback slot in case the Slots table is empty
    Returns:
        int: The maximum slot number, or the fallback slot if the table is empty.

    Raises:
        DatabaseError: If there is an error querying the database.
    """
    try:
        with Database() as db:
            db.execute(SELECT_MAX_SLOT_SQL, (fallback_slot,))
            result: tuple | None = db.fetchone()
            if result and result[0] is not None:
                return result[0]
            else:
                raise DatabaseMismatchError(
                    "While getting the max slot number from table Slots,\
                        fallback_slot was not taken into consideration."
                )
    except Exception as e:
        raise DatabaseError("Error getting the max slot number from table Slots.") from e


def filter_slots_by_proposer(min_slot: int) -> list[tuple[int, int, str, BigInteger, str]]:
    """
    Fetches slots proposed by our validators where the slot number
    is greater than the specified min_slot:
      * have not been processed before.
      * proposed by the known validators.

    Returns the proposer_index, block_number, fee_recipient, burned_amount,
    and the *expected* fee_recipient (which corresponds to the Pools' withdrawal_contract_address)
    for each slot.

    Args:
        min_slot (int): Minimum slot number to be considered.

    Returns:
        list[tuple]: A list of tuples, each containing:
            - SLOTS_BLOCK_NUMBER_FIELD (int): Index of the proposer.
            - SLOTS_PROPOSER_INDEX_FIELD (int): Block number.
            - SLOTS_FEE_RECIPIENT_FIELD (str): Address of the fee recipient.
            - SLOTS_BURNED_AMOUNT_FIELD (BigInteger): Amount burned.
            - POOLS_WITHDRAWAL_CONTRACT_ADDRESS_FIELD (str): Withdrawal contract address.

    Raises:
        DatabaseError: If there is an error fetching data from the database.
    """
    try:
        with Database() as db:
            db.execute(
                SELECT_PROPOSER_FILTERED_SLOTS_SQL,
                {
                    "min_slot": min_slot,
                },
            )
            results = db.fetchall()
            return results
    except Exception as e:
        raise DatabaseError(
            "Error fetching slots proposed by our validators from the database."
        ) from e
