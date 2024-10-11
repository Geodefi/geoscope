# -*- coding: utf-8 -*-
import json

from src.classes import Database
from src.exceptions.classes.database import DatabaseError
from src.globals import get_logger


def create_merkles_table() -> None:
    """Creates the sql database table for Merkles.

    Raises:
        DatabaseError: Error creating Merkles table
    """

    try:
        with Database() as db:
            # -- Root hash of the Merkle tree
            # -- Index of the item in the list
            # -- The associated value(s)
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS Merkles (
                    root_hash TEXT NOT NULL,      
                    item_values TEXT NOT NULL     
                )
                """
            )
        get_logger().debug(f"Created a new table: Merkles")
    except Exception as e:
        raise DatabaseError("Error creating Merkles table") from e


def drop_merkles_table() -> None:
    """Removes Merkles table from the database.

    Raises:
        DatabaseError: Error dropping Merkles table
    """

    try:
        with Database() as db:
            db.execute("""DROP TABLE IF EXISTS Merkles""")
        get_logger().debug(f"Dropped Table: Merkles")
    except Exception as e:
        raise DatabaseError(f"Error dropping Merkles table") from e


def reinitialize_merkles_table() -> None:
    """Removes Merkles table and creates an empty one."""

    drop_merkles_table()
    create_merkles_table()


def save_merkle_tree_json(root_hash, values_list):
    """
    Inserts a Merkle tree root and its associated list (as a whole) into the Merkles table.

    Parameters:
    - root_hash: The root hash of the Merkle tree
    - values_list: List of lists to insert (as a single JSON object)
    """
    try:
        with Database() as db:
            # Serialize the entire list to JSON
            data = {"root_hash": root_hash, "item_values": json.dumps(values_list)}

            # Perform the insertion with a single execute
            db.execute(
                """
                INSERT INTO Merkles (root_hash, item_values)
                VALUES (:root_hash, :item_values);
                """,
                data,
            )

        get_logger().debug(f"Inserted Merkle tree with root {root_hash} into Merkles table")

    except Exception as e:
        raise DatabaseError("Error inserting Merkle tree data") from e
