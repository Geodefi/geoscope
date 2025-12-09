"""
Functions to manage the Merkles table in the database.
"""

import json

from src.classes import Database
from src.database.utils.generators import (
    generate_create_table_sql,
    generate_drop_table_sql,
    generate_insert_sql,
)
from src.exceptions.classes.database import DatabaseError
from src.globals import get_logger
from src.globals.constants.database import (
    MERKLES_ROOT_HASH_FIELD,
    MERKLES_TABLE_KEY,
    MERKLES_TREE_JSON_FIELD,
)

# Pre-rendered SQL Statements
CREATE_TABLE_SQL: str = generate_create_table_sql(MERKLES_TABLE_KEY)
DROP_TABLE_SQL: str = generate_drop_table_sql(MERKLES_TABLE_KEY)
INSERT_SQL: str = generate_insert_sql(MERKLES_TABLE_KEY)


def create_merkles_table() -> None:
    """Creates the sql database table for Merkles.

    Raises:
        DatabaseError: Error creating Merkles table
    """

    try:
        with Database() as db:
            db.execute(CREATE_TABLE_SQL)
        get_logger().debug(f"Created a new table: {MERKLES_TABLE_KEY}")
    except Exception as e:
        raise DatabaseError(f"Error creating {MERKLES_TABLE_KEY} table") from e


def drop_merkles_table() -> None:
    """Removes Merkles table from the database.

    Raises:
        DatabaseError: Error dropping Merkles table
    """

    try:
        with Database() as db:
            db.execute(DROP_TABLE_SQL)
        get_logger().debug(f"Dropped Table: {MERKLES_TABLE_KEY}")
    except Exception as e:
        raise DatabaseError(f"Error dropping {MERKLES_TABLE_KEY} table") from e


def reinitialize_merkles_table() -> None:
    """Removes Merkles table and creates an empty one.

    Raises:
        DatabaseError: Error reinitializing Merkles table
    """
    try:
        with Database() as db:
            db.execute(DROP_TABLE_SQL)
            db.execute(CREATE_TABLE_SQL)
        get_logger().warning(f"Reinitialized table: {MERKLES_TABLE_KEY}")
    except DatabaseError as e:
        get_logger().error(f"Failed to reinitialize {MERKLES_TABLE_KEY} table.")
        raise e


def insert_merkle_tree_json(root_hash: str, values_list: list) -> None:
    """
    Inserts a Merkle tree root and tree as json string into the Merkles table.

    Parameters:
    - root_hash: The root hash of the Merkle tree
    - values_list: List of lists to insert (as a single JSON object)

    Raises:
        DatabaseError: If insertion into the database fails.
    """
    try:
        # Serialize the entire list to JSON
        data = {
            MERKLES_ROOT_HASH_FIELD: root_hash,
            MERKLES_TREE_JSON_FIELD: json.dumps(list(values_list)),
        }

        with Database() as db:
            db.execute(INSERT_SQL, data)

        get_logger().debug(
            f"Inserted Merkle tree with root {root_hash} into {MERKLES_TABLE_KEY} table"
        )

    except Exception as e:
        raise DatabaseError(
            f"Error inserting Merkle tree data into {MERKLES_TABLE_KEY} table"
        ) from e
