"""
Database table schemas.

`DATABASE_SCHEMA` is a dictionary mapping table names to their schema definitions.

Each schema definition is a dictionary mapping field names to their definitions,
where each field definition is itself a dictionary containing:

- `SCHEMA_TYPE_KEY`: The Python type of the field (e.g., `str`, `int`).
- `SCHEMA_SQL_TYPE_KEY`: The SQL data type of the field (e.g., `"TEXT"`, `"INTEGER"`).
- `SCHEMA_CONSTRAINTS_KEY`: Any SQL constraints for the field (e.g., `"NOT NULL"`, `"PRIMARY KEY"`).

**Assumptions:**

- We assume that the keys in `DATABASE_SCHEMA` are used directly as the table name in SQL statement.
- The field names within each schema are used as the column names in the tables.

**Notes:**

- The Python type of a field can differ from the SQL type. In such cases, 
functions from the `convertors.py` module should be utilized to convert between types as needed.
"""

from typing import Any

from src.common import BigInteger
from src.globals.constants.database import (
    DEPOSITS_AMOUNT_FIELD,
    DEPOSITS_PUBKEY_FIELD,
    DEPOSITS_SIGNATURE_FIELD,
    DEPOSITS_SLOT_FIELD,
    DEPOSITS_TABLE_KEY,
    DEPOSITS_WITHDRAWAL_CREDENTIALS_FIELD,
    MERKLES_ROOT_HASH_FIELD,
    MERKLES_TABLE_KEY,
    MERKLES_TREE_JSON_FIELD,
    POOLS_FULFILLED_ETHER_BALANCE_FIELD,
    POOLS_NAME_FIELD,
    POOLS_POOL_ID_FIELD,
    POOLS_PRICE_FIELD,
    POOLS_SECURED_FIELD,
    POOLS_SURPLUS_FIELD,
    POOLS_TABLE_KEY,
    POOLS_TOTAL_SUPPLY_FIELD,
    POOLS_WITHDRAWAL_CONTRACT_ADDRESS_FIELD,
    POOLS_WITHDRAWAL_CREDENTIALS_FIELD,
    SCHEMA_CONSTRAINTS_KEY,
    SCHEMA_SQL_TYPE_KEY,
    SCHEMA_TYPE_KEY,
    SLOTS_BLOCK_NUMBER_FIELD,
    SLOTS_BURNED_AMOUNT_FIELD,
    SLOTS_FEE_RECIPIENT_FIELD,
    SLOTS_PROPOSER_INDEX_FIELD,
    SLOTS_SLOT_FIELD,
    SLOTS_TABLE_KEY,
    VALIDATORS_BEACON_INDEX_FIELD,
    VALIDATORS_EXIT_EPOCH_FIELD,
    VALIDATORS_FEE_RECIPIENT_BALANCE_FIELD,
    VALIDATORS_INFRASTRUCTURE_FEE_FIELD,
    VALIDATORS_LAST_WITHDRAWN_FIELD,
    VALIDATORS_OPERATOR_FEE_FIELD,
    VALIDATORS_OPERATOR_ID_FIELD,
    VALIDATORS_POOL_FEE_FIELD,
    VALIDATORS_POOL_ID_FIELD,
    VALIDATORS_PORTAL_INDEX_FIELD,
    VALIDATORS_PROPOSAL_SIGNATURE_FIELD,
    VALIDATORS_PROPOSAL_SLOT_FIELD,
    VALIDATORS_PUBKEY_FIELD,
    VALIDATORS_SIGNATURE31_FIELD,
    VALIDATORS_STAKE_SIGNATURE_FIELD,
    VALIDATORS_TABLE_KEY,
    VALIDATORS_WITHDRAWAL_CREDENTIALS_FIELD,
    VALIDATORS_WITHDRAWN_BALANCE_FIELD,
    WITHDRAWALS_ADDRESS_FIELD,
    WITHDRAWALS_AMOUNT_FIELD,
    WITHDRAWALS_SLOT_FIELD,
    WITHDRAWALS_TABLE_KEY,
    WITHDRAWALS_VALIDATOR_INDEX_FIELD,
)

# Mapping of table keys to their schemas
DATABASE_SCHEMA: dict[str, dict[str, dict[str, Any]]] = {
    MERKLES_TABLE_KEY: {
        MERKLES_ROOT_HASH_FIELD: {
            SCHEMA_TYPE_KEY: str,
            SCHEMA_SQL_TYPE_KEY: "TEXT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL PRIMARY KEY",
        },
        MERKLES_TREE_JSON_FIELD: {
            SCHEMA_TYPE_KEY: str,
            SCHEMA_SQL_TYPE_KEY: "TEXT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL",
        },
    },
    DEPOSITS_TABLE_KEY: {
        DEPOSITS_PUBKEY_FIELD: {
            SCHEMA_TYPE_KEY: str,
            SCHEMA_SQL_TYPE_KEY: "TEXT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL",
        },
        DEPOSITS_SIGNATURE_FIELD: {
            SCHEMA_TYPE_KEY: str,
            SCHEMA_SQL_TYPE_KEY: "TEXT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL",
        },
        DEPOSITS_WITHDRAWAL_CREDENTIALS_FIELD: {
            SCHEMA_TYPE_KEY: str,
            SCHEMA_SQL_TYPE_KEY: "TEXT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL",
        },
        DEPOSITS_AMOUNT_FIELD: {
            SCHEMA_TYPE_KEY: BigInteger,
            SCHEMA_SQL_TYPE_KEY: "BIGINT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL DEFAULT '{BigInteger.TYPE_PREFIX}0'",
        },
        DEPOSITS_SLOT_FIELD: {
            SCHEMA_TYPE_KEY: int,
            SCHEMA_SQL_TYPE_KEY: "INTEGER",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL",
        },
    },
    WITHDRAWALS_TABLE_KEY: {
        WITHDRAWALS_VALIDATOR_INDEX_FIELD: {
            SCHEMA_TYPE_KEY: int,
            SCHEMA_SQL_TYPE_KEY: "INTEGER",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL",
        },
        WITHDRAWALS_ADDRESS_FIELD: {
            SCHEMA_TYPE_KEY: str,
            SCHEMA_SQL_TYPE_KEY: "TEXT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL",
        },
        WITHDRAWALS_AMOUNT_FIELD: {
            SCHEMA_TYPE_KEY: BigInteger,
            SCHEMA_SQL_TYPE_KEY: "BIGINT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL DEFAULT '{BigInteger.TYPE_PREFIX}0'",
        },
        WITHDRAWALS_SLOT_FIELD: {
            SCHEMA_TYPE_KEY: int,
            SCHEMA_SQL_TYPE_KEY: "INTEGER",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL",
        },
    },
    POOLS_TABLE_KEY: {
        POOLS_POOL_ID_FIELD: {
            SCHEMA_TYPE_KEY: BigInteger,
            SCHEMA_SQL_TYPE_KEY: "BIGINT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL DEFAULT '{BigInteger.TYPE_PREFIX}0' PRIMARY KEY",
        },
        POOLS_NAME_FIELD: {
            SCHEMA_TYPE_KEY: str,
            SCHEMA_SQL_TYPE_KEY: "TEXT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL",
        },
        POOLS_WITHDRAWAL_CONTRACT_ADDRESS_FIELD: {
            SCHEMA_TYPE_KEY: str,
            SCHEMA_SQL_TYPE_KEY: "TEXT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL",
        },
        POOLS_WITHDRAWAL_CREDENTIALS_FIELD: {
            SCHEMA_TYPE_KEY: str,
            SCHEMA_SQL_TYPE_KEY: "TEXT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL",
        },
        POOLS_PRICE_FIELD: {
            SCHEMA_TYPE_KEY: BigInteger,
            SCHEMA_SQL_TYPE_KEY: "BIGINT",
            SCHEMA_CONSTRAINTS_KEY: f"DEFAULT '{BigInteger.TYPE_PREFIX}0'",
        },
        POOLS_TOTAL_SUPPLY_FIELD: {
            SCHEMA_TYPE_KEY: BigInteger,
            SCHEMA_SQL_TYPE_KEY: "BIGINT",
            SCHEMA_CONSTRAINTS_KEY: f"DEFAULT '{BigInteger.TYPE_PREFIX}0'",
        },
        POOLS_SURPLUS_FIELD: {
            SCHEMA_TYPE_KEY: BigInteger,
            SCHEMA_SQL_TYPE_KEY: "BIGINT",
            SCHEMA_CONSTRAINTS_KEY: f"DEFAULT '{BigInteger.TYPE_PREFIX}0'",
        },
        POOLS_SECURED_FIELD: {
            SCHEMA_TYPE_KEY: BigInteger,
            SCHEMA_SQL_TYPE_KEY: "BIGINT",
            SCHEMA_CONSTRAINTS_KEY: f"DEFAULT '{BigInteger.TYPE_PREFIX}0'",
        },
        POOLS_FULFILLED_ETHER_BALANCE_FIELD: {
            SCHEMA_TYPE_KEY: BigInteger,
            SCHEMA_SQL_TYPE_KEY: "BIGINT",
            SCHEMA_CONSTRAINTS_KEY: f"DEFAULT'{BigInteger.TYPE_PREFIX}0'",
        },
    },
    SLOTS_TABLE_KEY: {
        SLOTS_SLOT_FIELD: {
            SCHEMA_TYPE_KEY: int,
            SCHEMA_SQL_TYPE_KEY: "INTEGER",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL PRIMARY KEY",
        },
        SLOTS_BLOCK_NUMBER_FIELD: {
            SCHEMA_TYPE_KEY: int,
            SCHEMA_SQL_TYPE_KEY: "INTEGER",
            SCHEMA_CONSTRAINTS_KEY: "UNIQUE",
        },
        SLOTS_PROPOSER_INDEX_FIELD: {
            SCHEMA_TYPE_KEY: int,
            SCHEMA_SQL_TYPE_KEY: "INTEGER",
            SCHEMA_CONSTRAINTS_KEY: "",
        },
        SLOTS_FEE_RECIPIENT_FIELD: {
            SCHEMA_TYPE_KEY: str,
            SCHEMA_SQL_TYPE_KEY: "TEXT",
            SCHEMA_CONSTRAINTS_KEY: "",
        },
        SLOTS_BURNED_AMOUNT_FIELD: {
            SCHEMA_TYPE_KEY: BigInteger,
            SCHEMA_SQL_TYPE_KEY: "BIGINT",
            SCHEMA_CONSTRAINTS_KEY: "DEFAULT '{BigInteger.TYPE_PREFIX}0'",
        },
    },
    VALIDATORS_TABLE_KEY: {
        VALIDATORS_PUBKEY_FIELD: {
            SCHEMA_TYPE_KEY: str,
            SCHEMA_SQL_TYPE_KEY: "TEXT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL PRIMARY KEY",
        },
        VALIDATORS_PORTAL_INDEX_FIELD: {
            SCHEMA_TYPE_KEY: int,
            SCHEMA_SQL_TYPE_KEY: "INTEGER",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL UNIQUE",
        },
        VALIDATORS_POOL_ID_FIELD: {
            SCHEMA_TYPE_KEY: BigInteger,
            SCHEMA_SQL_TYPE_KEY: "BIGINT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL DEFAULT '{BigInteger.TYPE_PREFIX}0'",
        },
        VALIDATORS_OPERATOR_ID_FIELD: {
            SCHEMA_TYPE_KEY: BigInteger,
            SCHEMA_SQL_TYPE_KEY: "BIGINT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL DEFAULT '{BigInteger.TYPE_PREFIX}0'",
        },
        VALIDATORS_POOL_FEE_FIELD: {
            SCHEMA_TYPE_KEY: BigInteger,
            SCHEMA_SQL_TYPE_KEY: "BIGINT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL DEFAULT '{BigInteger.TYPE_PREFIX}0'",
        },
        VALIDATORS_OPERATOR_FEE_FIELD: {
            SCHEMA_TYPE_KEY: BigInteger,
            SCHEMA_SQL_TYPE_KEY: "BIGINT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL DEFAULT '{BigInteger.TYPE_PREFIX}0'",
        },
        VALIDATORS_INFRASTRUCTURE_FEE_FIELD: {
            SCHEMA_TYPE_KEY: BigInteger,
            SCHEMA_SQL_TYPE_KEY: "BIGINT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL DEFAULT '{BigInteger.TYPE_PREFIX}0'",
        },
        VALIDATORS_SIGNATURE31_FIELD: {
            SCHEMA_TYPE_KEY: str,
            SCHEMA_SQL_TYPE_KEY: "TEXT",
            SCHEMA_CONSTRAINTS_KEY: "NOT NULL UNIQUE",
        },
        VALIDATORS_BEACON_INDEX_FIELD: {
            SCHEMA_TYPE_KEY: int,
            SCHEMA_SQL_TYPE_KEY: "INTEGER",
            SCHEMA_CONSTRAINTS_KEY: "",
        },
        VALIDATORS_WITHDRAWAL_CREDENTIALS_FIELD: {
            SCHEMA_TYPE_KEY: str,
            SCHEMA_SQL_TYPE_KEY: "TEXT",
            SCHEMA_CONSTRAINTS_KEY: "",
        },
        VALIDATORS_EXIT_EPOCH_FIELD: {  # TODO:(crash) This might be wrong
            SCHEMA_TYPE_KEY: int,
            SCHEMA_SQL_TYPE_KEY: "INTEGER",
            SCHEMA_CONSTRAINTS_KEY: "",
        },
        VALIDATORS_PROPOSAL_SIGNATURE_FIELD: {
            SCHEMA_TYPE_KEY: str,
            SCHEMA_SQL_TYPE_KEY: "TEXT",
            SCHEMA_CONSTRAINTS_KEY: "",
        },
        VALIDATORS_STAKE_SIGNATURE_FIELD: {
            SCHEMA_TYPE_KEY: str,
            SCHEMA_SQL_TYPE_KEY: "TEXT",
            SCHEMA_CONSTRAINTS_KEY: "",
        },
        VALIDATORS_PROPOSAL_SLOT_FIELD: {
            SCHEMA_TYPE_KEY: int,
            SCHEMA_SQL_TYPE_KEY: "INTEGER",
            SCHEMA_CONSTRAINTS_KEY: "",
        },
        VALIDATORS_WITHDRAWN_BALANCE_FIELD: {
            SCHEMA_TYPE_KEY: BigInteger,
            SCHEMA_SQL_TYPE_KEY: "BIGINT DEFAULT '{BigInteger.TYPE_PREFIX}0'",
            SCHEMA_CONSTRAINTS_KEY: "",
        },
        VALIDATORS_LAST_WITHDRAWN_FIELD: {
            SCHEMA_TYPE_KEY: BigInteger,
            SCHEMA_SQL_TYPE_KEY: "BIGINT DEFAULT '{BigInteger.TYPE_PREFIX}0'",
            SCHEMA_CONSTRAINTS_KEY: "",
        },
        VALIDATORS_FEE_RECIPIENT_BALANCE_FIELD: {
            SCHEMA_TYPE_KEY: BigInteger,
            SCHEMA_SQL_TYPE_KEY: "BIGINT DEFAULT '{BigInteger.TYPE_PREFIX}0'",
            SCHEMA_CONSTRAINTS_KEY: "",
        },
    },
    # Add other table schemas here
}
