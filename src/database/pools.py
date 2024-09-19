# src/database/pools.py

from src.classes import Database
from src.exceptions.classes.database import DatabaseError
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
                    totalSupply TEXT,
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
        pools (list[dict]): List of pool records to insert

    Raises:
        DatabaseError: Error inserting many pools into table
    """
    try:
        with Database() as db:
            db.executemany(
                """
                INSERT INTO Pools (id, name, price, totalSupply, withdrawal_contract, surplus, secured, fulfilled_ether_balance)
                VALUES (:id, :name, :price, :totalSupply, :withdrawal_contract, :surplus, :secured, :fulfilled_ether_balance)
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
    """
    try:
        with Database() as db:
            db.execute("SELECT 1 FROM Pools WHERE id = ?", (pool_id,))
            result = db.fetchone()
        return result is not None
    except Exception as e:
        raise DatabaseError(f"Error checking pool by ID") from e


def update_multiple_pools(pool_updates: list[dict]) -> None:
    """Updates specified fields in the Pools table for multiple pool IDs.

    Args:
        pool_updates (list): List of dictionaries containing pool_id, price, totalSupply, surplus, secured, fulfilled_ether_balance

    Raises:
        DatabaseError: Error updating pool fields
    """
    try:
        with Database() as db:
            for update in pool_updates:
                db.execute(
                    """
                    UPDATE Pools
                    SET price = :price, totalSupply = :totalSupply, surplus = :surplus, secured = :secured, fulfilled_ether_balance = :fulfilled_ether_balance
                    WHERE id = :pool_id
                    """,
                    update,
                )
            get_logger().debug(f"Updated multiple pools with new values")
    except Exception as e:
        raise DatabaseError("Error updating multiple pool fields") from e
