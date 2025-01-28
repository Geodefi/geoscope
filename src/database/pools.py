"""
Functions to manage the Pools table in the database.
"""

from src.classes import Database
from src.common import BigInteger
from src.database.utils.generators import (
    Condition,
    generate_count_sql,
    generate_create_table_sql,
    generate_drop_table_sql,
    generate_insert_sql,
    generate_select_exists_sql,
    generate_select_fields_sql,
    generate_select_fields_where_conditions_sql,
    generate_select_fields_where_in_sql,
    generate_update_where_conditions_sql,
)
from src.exceptions.classes.database import DatabaseError, DatabaseMismatchError
from src.globals import get_logger
from src.globals.constants.database import (
    POOLS_FULFILLED_ETHER_BALANCE_FIELD,
    POOLS_POOL_ID_FIELD,
    POOLS_PRICE_FIELD,
    POOLS_SECURED_FIELD,
    POOLS_SURPLUS_FIELD,
    POOLS_TABLE_KEY,
    POOLS_TOTAL_SUPPLY_FIELD,
    POOLS_WITHDRAWAL_CONTRACT_ADDRESS_FIELD,
)

# Pre-rendered SQL Statements
CREATE_TABLE_SQL: str = generate_create_table_sql(POOLS_TABLE_KEY)
DROP_TABLE_SQL: str = generate_drop_table_sql(POOLS_TABLE_KEY)
INSERT_SQL: str = generate_insert_sql(POOLS_TABLE_KEY, only_not_null_fields=True)
CHECK_POOL_ID_EXISTS_SQL: str = generate_select_exists_sql(POOLS_TABLE_KEY, POOLS_POOL_ID_FIELD)
COUNT_POOLS_SQL: str = generate_count_sql(POOLS_TABLE_KEY)
SELECT_POOL_IDS_SQL: str = generate_select_fields_sql(POOLS_TABLE_KEY, POOLS_POOL_ID_FIELD)
SELECT_WITHDRAWAL_CONTRACT_ADDRESS_SQL: str = generate_select_fields_where_conditions_sql(
    POOLS_TABLE_KEY,
    [Condition(field=POOLS_POOL_ID_FIELD, operator="=")],
    POOLS_WITHDRAWAL_CONTRACT_ADDRESS_FIELD,
)
SET_POOL_DATA_SQL = generate_update_where_conditions_sql(
    POOLS_TABLE_KEY,
    [Condition(field=POOLS_POOL_ID_FIELD, operator="=")],
    POOLS_PRICE_FIELD,
    POOLS_TOTAL_SUPPLY_FIELD,
    POOLS_SURPLUS_FIELD,
    POOLS_SECURED_FIELD,
    POOLS_FULFILLED_ETHER_BALANCE_FIELD,
)


def create_pools_table() -> None:
    """Creates the sql database table for Pools.
    Raises:
        DatabaseError: Error creating Pools table
    """
    try:
        with Database() as db:
            db.execute(CREATE_TABLE_SQL)
        get_logger().debug(f"Created a new table: {POOLS_TABLE_KEY}")
    except Exception as e:
        raise DatabaseError(f"Error creating {POOLS_TABLE_KEY} table") from e


def drop_pools_table() -> None:
    """Removes Pools table from the database.

    Raises:
        DatabaseError: Error dropping Pools table
    """

    try:
        with Database() as db:
            db.execute(DROP_TABLE_SQL)
        get_logger().debug(f"Dropped Table: {POOLS_TABLE_KEY}")
    except Exception as e:
        raise DatabaseError(f"Error dropping {POOLS_TABLE_KEY} table") from e


def reinitialize_pools_table() -> None:
    """Removes Pools table and creates an empty one."""
    try:
        with Database() as db:
            db.execute(DROP_TABLE_SQL)
            db.execute(CREATE_TABLE_SQL)
        get_logger().warning(f"Reinitialized table: {POOLS_TABLE_KEY}")
    except DatabaseError as e:
        get_logger().error(f"Failed to reinitialize {POOLS_TABLE_KEY} table.")
        raise e


def insert_pools_batch(pools: list[dict[str, BigInteger | str]]) -> None:
    """
    Inserts multiple pools into the Pools table, with only the required (NOT NULL) fields.

    Args:
        pools (list[dict[str, Any]]): List of pool records to insert.
            Each record must include the following required fields:
                - pool_id (BigInteger): The unique identifier of the pool.
                - name (str): The name of the pool.
                - withdrawal_contract_address (str): The contract address for withdrawals.
                - withdrawal_credentials (str): The withdrawal credentials.
    Raises:
        DatabaseError: If insertion into the database fails.
    """
    try:
        with Database() as db:
            db.executemany(INSERT_SQL, pools)
        get_logger().debug(f"Inserted {len(pools)} records into {POOLS_TABLE_KEY} table")
    except Exception as e:
        raise DatabaseError(f"Error inserting pools into table {POOLS_TABLE_KEY}") from e


def read_pool_count() -> int:
    """
    Returns the number of pools in the database.

    Returns:
        int: Number of pools in the database

    Raises:
        DatabaseError: If there is an error counting pools in the table.
    """
    try:
        with Database() as db:
            db.execute(COUNT_POOLS_SQL)
            result = db.fetchone()
            if result:
                return result[0]
            return 0
    except Exception as e:
        raise DatabaseError(f"Error counting pools in table {POOLS_TABLE_KEY}") from e


def read_pool_ids() -> list[BigInteger]:
    """
    Returns all the pool IDs from the database.

    Returns:
        list[BigInteger]: List of pool IDs.

    Raises:
        DatabaseError: If there is an error retrieving pool IDs from the table.
    """
    try:
        with Database() as db:
            db.execute(SELECT_POOL_IDS_SQL)
            rows = db.fetchall()
            return [row[0] for row in rows]  # Assuming IDs are integers
    except Exception as e:
        raise DatabaseError(f"Error getting all pool IDs from table {POOLS_TABLE_KEY}") from e


def read_withdrawal_contract_address(pool_id: BigInteger) -> str:
    """
    Retrieves the withdrawal contract address for a given pool ID.

    Args:
        pool_id (BigInteger): The ID of the pool.

    Returns:
        str: The withdrawal contract address of the pool.

    Raises:
        DatabaseError: If there is an error querying the database.
        DatabaseMismatchError: If the pool does not have a withdrawal contract address.
    """
    try:
        with Database() as db:
            db.execute(SELECT_WITHDRAWAL_CONTRACT_ADDRESS_SQL, {POOLS_POOL_ID_FIELD: pool_id})
            result = db.fetchone()
            if result:
                if result[0]:
                    return result[0]
            raise DatabaseMismatchError(
                f"Pool with ID {pool_id} does not have a withdrawal contract address"
            )
    except Exception as e:
        raise DatabaseError(
            f"Error fetching withdrawal contract address from table {POOLS_TABLE_KEY}"
        ) from e


def read_latest_pool_data_batch(
    pool_ids: list[BigInteger],
) -> list[
    tuple[
        BigInteger,
        BigInteger,
        BigInteger,
        BigInteger,
        BigInteger,
        BigInteger,
    ]
]:
    """
    Fetches the latest data for a batch of pools from the database.
    This data is updated previously while indexing the slots.

    Args:
        pool_ids (list[BigInteger]): List of pool IDs.

    Returns:
        list[tuple]: A list of tuples containing the latest data for the pools.
            Each tuple contains the following fields in order:
                - pool_id (BigInteger)
                - price (BigInteger)
                - total_supply (BigInteger)
                - surplus (BigInteger)
                - secured (BigInteger)
                - fulfilled_ether_balance (BigInteger)

    Raises:
        DatabaseError: If there is an error fetching data from the Pools table.
    """
    try:
        select_fields = [
            POOLS_POOL_ID_FIELD,
            POOLS_PRICE_FIELD,
            POOLS_TOTAL_SUPPLY_FIELD,
            POOLS_SURPLUS_FIELD,
            POOLS_SECURED_FIELD,
            POOLS_FULFILLED_ETHER_BALANCE_FIELD,
        ]
        sql = generate_select_fields_where_in_sql(
            POOLS_TABLE_KEY, select_fields, POOLS_POOL_ID_FIELD, num_values=len(pool_ids)
        )
        with Database() as db:
            db.execute(sql, pool_ids)
            rows = db.fetchall()
            return rows
    except Exception as e:
        raise DatabaseError("Error fetching latest data of pools from table Pools") from e


def check_pool_by_id(pool_id: BigInteger) -> bool:
    """
    Checks if there are any pools saved in the database for the pool id.

    Args:
        pool_id (BigInteger): 'ID' of the pool to check

    Returns:
        bool: True if the pool exists, False otherwise

    Raises:
        DatabaseError: If there is an error querying the database.
    """
    try:
        with Database() as db:
            db.execute(CHECK_POOL_ID_EXISTS_SQL, {POOLS_POOL_ID_FIELD: pool_id})
            return db.fetchone() is not None
    except Exception as e:
        raise DatabaseError(
            f"Error checking if pool_id{pool_id} is in table {POOLS_POOL_ID_FIELD}"
        ) from e


def update_pool_data_batch(pool_updates: list[dict[str, BigInteger]]) -> None:
    """Updates specified fields in the Pools table for multiple pool IDs.

    Args:
        pool_updates (list[dict[str, BigInteger]]):
            A list of dictionaries where each dictionary contains the following keys:
                - 'pool_id' (BigInteger): The ID of the pool to update.
                - 'price' (BigInteger): The new price of the pool.
                - 'total_supply' (BigInteger): The updated total supply of the pool.
                - 'surplus' (BigInteger): The updated surplus of the pool.
                - 'secured' (BigInteger): The updated secured amount of the pool.
                - 'fulfilled_ether_balance' (BigInteger): The updated fulfilled balance in ETH.

    Raises:
        DatabaseError: If there is an error updating the pool fields in the database.
    """
    try:
        with Database() as db:
            for update in pool_updates:
                db.execute(SET_POOL_DATA_SQL, update)
            get_logger().debug("Updated multiple pools with new values")
    except Exception as e:
        raise DatabaseError("Error updating multiple pool fields") from e
