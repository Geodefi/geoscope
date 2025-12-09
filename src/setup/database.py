from typing import Any

from src.database.deposits import create_deposits_table, reinitialize_deposits_table
from src.database.merkles import create_merkles_table, reinitialize_merkles_table
from src.database.pools import create_pools_table, reinitialize_pools_table
from src.database.slots import create_slots_table, reinitialize_slots_table
from src.database.validators import create_validators_table, reinitialize_validators_table
from src.database.withdrawals import create_withdrawals_table, reinitialize_withdrawals_table
from src.exceptions import DatabaseInitializationError
from src.globals.constants.database import (
    DEPOSITS_TABLE_KEY,
    MERKLES_TABLE_KEY,
    POOLS_TABLE_KEY,
    SLOTS_TABLE_KEY,
    VALIDATORS_TABLE_KEY,
    WITHDRAWALS_TABLE_KEY,
)


def create_db_tables(*args: Any) -> None:
    """
    Create specified database tables, for the Geoscope application.
    Ensures all tables are available, creates the missing tables if any.
    Will not fail if given Table already exists.

    Args: Table keys to create:
    - DEPOSITS_TABLE_KEY: Deposits
    - SLOTS_TABLE_KEY: Slots
    - VALIDATORS_TABLE_KEY: Validators
    - POOLS_TABLE_KEY: Pools
    - WITHDRAWALS_TABLE_KEY: Withdrawals
    - MERKLES_TABLE_KEY: Merkles

    Raises:
        DatabaseInitializationError: If a table creation fails.
    """

    try:
        if DEPOSITS_TABLE_KEY in args:
            create_deposits_table()
        if POOLS_TABLE_KEY in args:
            create_pools_table()
        if SLOTS_TABLE_KEY in args:
            create_slots_table()
        if VALIDATORS_TABLE_KEY in args:
            create_validators_table()
        if WITHDRAWALS_TABLE_KEY in args:
            create_withdrawals_table()
        if MERKLES_TABLE_KEY in args:
            create_merkles_table()

    except Exception as e:
        raise DatabaseInitializationError from e


def reinitialize_db_tables(*args: Any) -> None:
    """
    Reinitializes specified database tables, for the Geoscope application.
    Ensures all tables are wiped out, creates the missing tables if any.
    Will not fail if given Table already exists, BUT WILL WIPE ITS DATA.

    Args: Table keys to reinitialize:
    - DEPOSITS_TABLE_KEY: Deposits
    - SLOTS_TABLE_KEY: Slots
    - VALIDATORS_TABLE_KEY: Validators
    - POOLS_TABLE_KEY: Pools
    - WITHDRAWALS_TABLE_KEY: Withdrawals
    - MERKLES_TABLE_KEY: Merkles

    Raises:
        DatabaseInitializationError: If a table reinitialization fails.
    """

    try:
        if DEPOSITS_TABLE_KEY in args:
            reinitialize_deposits_table()

        if POOLS_TABLE_KEY in args:
            reinitialize_pools_table()

        if SLOTS_TABLE_KEY in args:
            reinitialize_slots_table()

        if VALIDATORS_TABLE_KEY in args:
            reinitialize_validators_table()

        if WITHDRAWALS_TABLE_KEY in args:
            reinitialize_withdrawals_table()

        if MERKLES_TABLE_KEY in args:
            reinitialize_merkles_table()

    except Exception as e:
        raise DatabaseInitializationError from e
