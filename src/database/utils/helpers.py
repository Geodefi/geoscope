"""
Helper functions for working with database schemas and SQL identifiers.
"""

import re
from typing import Any

from src.globals.schemas.database import DATABASE_SCHEMA


def quote_identifier(name: str) -> str:
    """
    Sanitizes and quotes an SQL identifier (e.g., table name or column name).

    Args:
        name (str): The identifier to sanitize and quote.

    Returns:
        str: The sanitized and quoted identifier.

    Raises:
        ValueError: If the identifier contains invalid characters.
    """
    # Regular expression to match valid SQL identifiers (letters, numbers, underscores)
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        return f'"{name}"'
    else:
        raise ValueError(f"Invalid SQL identifier: {name}")


def get_table_schema(table_key: str) -> dict[str, dict[str, Any]]:
    """
    Retrieves the schema for a specified table.

    Args:
        table_key (str): The key identifier for the table.

    Returns:
        TypedDict: The schema of the table.

    Raises:
        ValueError: If the table key is not found.
    """
    try:
        return DATABASE_SCHEMA[table_key]
    except KeyError as e:
        raise ValueError(f"Table key '{table_key}' not found in TABLE_SCHEMAS.") from e
