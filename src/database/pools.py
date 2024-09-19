# src/database/pools.py

from src.classes import Database
from src.exceptions.classes.database import DatabaseError, DatabaseMismatchError
from src.globals import get_logger


def create_pools_table() -> None:
    """Creates the sql database table for Pools.

    Raises:
        DatabaseError: Error creating Pools table
    """
    try:
        with Database() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS Pools (
                    id TEXT NOT NULL PRIMARY KEY,
                    name TEXT NOT NULL,
                    withdrawal_contract_address TEXT NOT NULL,
                    price TEXT,
                    total_supply TEXT,
                    surplus TEXT,
                    secured TEXT,
                    fulfilled_ether_balance TEXT
                )
                """
            )
        get_logger().debug(f"Created a new table: Pools")
    except Exception as e:
        raise DatabaseError("Error creating Pools table") from e


def drop_pools_table() -> None:
    """Removes Pools table from the database.

    Raises:
        DatabaseError: Error dropping Pools table
    """
    try:
        with Database() as db:
            db.execute("""DROP TABLE IF EXISTS Pools""")
        get_logger().debug(f"Dropped Table: Pools")
    except Exception as e:
        raise DatabaseError(f"Error dropping Pools table") from e


def reinitialize_pools_table() -> None:
    """Removes Pools table and creates an empty one."""
    drop_pools_table()
    create_pools_table()


def insert_many_pools(pools: list[dict]) -> None:
    """
    Inserts multiple pool records into the Pools table.

    Args:
        pools (list[dict]): List of pool records to insert [{id, name, withdrawal_contract_address}...]

    Raises:
        DatabaseError: Error inserting many pools into table
    """
    try:
        with Database() as db:
            db.executemany(
                """
                INSERT INTO Pools (id, name, withdrawal_contract_address)
                VALUES (:id, :name, :withdrawal_contract_address)
                """,
                pools,
            )
        get_logger().debug(f"Inserted {len(pools)} records into Pools table")
    except Exception as e:
        raise DatabaseError(f"Error inserting many pools into table") from e


def check_pool_by_id(pool_id: int) -> bool:
    """Checks if a pool exists in the database by its ID.

    Args:
        pool_id (int): ID of the pool to check

    Returns:
        bool: True if the pool exists, False otherwise

    Raises:
        DatabaseMismatchError: There are more tahn 1 Pools with the same ID.
        DatabaseError: Error checking if pubkey is in table Validators
    """
    try:
        with Database() as db:
            db.execute("SELECT * FROM Pools WHERE id = ?", (pool_id,))
            result = db.fetchall()
            if result:
                if len(result) == 1:
                    return True
                else:
                    raise DatabaseMismatchError(
                        f"There are {len(result)} Pools with the same ID in table Pools"
                    )
            return False
    except Exception as e:
        raise DatabaseError(f"Error checking pool by ID in table Pools") from e


def update_multiple_pools(pool_updates: list[dict]) -> None:
    """Updates specified fields in the Pools table for multiple pool IDs.

    Args:
        pool_updates (list): List of dictionaries containing pool_id, price, total_supply, surplus, secured, fulfilled_ether_balance

    Raises:
        DatabaseError: Error updating pool fields
    """
    try:
        with Database() as db:
            for update in pool_updates:
                db.execute(
                    """
                    UPDATE Pools
                    SET price = :price, total_supply = :total_supply, surplus = :surplus, secured = :secured, fulfilled_ether_balance = :fulfilled_ether_balance
                    WHERE id = :pool_id
                    """,
                    update,
                )
            get_logger().debug(f"Updated multiple pools with new values")
    except Exception as e:
        raise DatabaseError("Error updating multiple pool fields") from e


def pool_count() -> int:
    """Returns the number of pools in the database.

    Returns:
        int: Number of pools in the database

    Raises:
        DatabaseError: Error counting pools in table Pools
    """
    try:
        with Database() as db:
            db.execute("SELECT COUNT(*) FROM Pools")
            return db.fetchone()[0]
    except Exception as e:
        raise DatabaseError("Error counting pools in table Pools") from e


def get_all_pool_ids() -> list[int]:
    """Returns all the pool ids from the database.

    Returns:
        list: list of pool ids

    Raises:
        DatabaseError: Error getting all pool ids from table Pools
    """
    try:
        with Database() as db:
            db.execute("SELECT id FROM Pools")
            return [int(row[0]) for row in db.fetchall()]
    except Exception as e:
        raise DatabaseError("Error getting all pool ids from table Pools") from e
