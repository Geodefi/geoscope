# big_integer.py

"""
`BigInteger` class, a subclass of `int` used to represent large integer values
that may exceed SQLite's INTEGER limits. 
The class includes methods for adapting to and converting from
SQLite types, allowing seamless integration with SQLite databases.

The `BigInteger` class is designed to work with SQLite's adapter and converter mechanisms, enabling
automatic handling of large integer values during database operations.
"""

import sqlite3


class BigInteger(int):
    """
    A subclass of `int` to represent large integer values that may exceed SQLite's INTEGER limits.

    This class includes methods for adapting to and converting from SQLite types, allowing it to
    be stored and retrieved from SQLite databases using custom types.

    Usage:
        - Wrap integer values with `BigInteger` when inserting into the database.
        - SQLite will use the adapter and converter methods for `BigInteger` instances.
    """

    # Prefix prevents the number being interpreted as REAL or INT instead of TEXT,
    # which causes scientific notation interpretation.
    TYPE_PREFIX = "B"

    def __str__(self) -> str:
        """
        Return the string representation of the `BigInteger`.

        Returns:
            str: The string representation of the integer value.
        """
        return str(int(self))

    def __repr__(self) -> str:
        return str(int(self))

    @staticmethod
    def adapt(value: int) -> str:
        """
        Adapter function to convert a `BigInteger` instance to a string for storage in SQLite.

        SQLite has a limitation on the size of integers it can store in the `INTEGER` type.
        By converting large integers to strings (`TEXT`), it stores values that exceed this limit.
        This adapter is registered with SQLite to handle `BigInteger` instances specifically,
        ensuring other integers are not affected.

        Args:
            value (BigInteger): The `BigInteger` value to adapt for storage.

        Returns:
            str: The string representation of the `BigInteger` value.
        """
        try:
            return f"{BigInteger.TYPE_PREFIX}{value}"
        except (OverflowError, ValueError) as e:
            raise ValueError(f"Cannot adapt value as BIGINT: {value}") from e

    @staticmethod
    def convert(value: bytes) -> "BigInteger":
        """
        Converter function to convert a TEXT value from SQLite back into a `BigInteger` instance.

        When retrieving data from SQLite, this converter transforms the stored `TEXT` value
        back into a `BigInteger`. This function is registered with SQLite to handle values
        stored with the custom SQL type name (e.g., `BIGINT`).

        Args:
            value (bytes): The byte-string value retrieved from SQLite.

        Returns:
            BigInteger: The `BigInteger` instance representing the original integer value.
        """
        try:
            value_str = value.decode().strip()
            if value_str.startswith(BigInteger.TYPE_PREFIX):
                return BigInteger(value_str[len(BigInteger.TYPE_PREFIX) :])
            raise ValueError(f"Invalid BigInteger format: {value_str}")
        except (ValueError, UnicodeDecodeError) as e:
            raise ValueError(f"Cannot convert value to BIGINT: {value.decode()}") from e


# Register the adapter and converter with SQLite
sqlite3.register_adapter(BigInteger, BigInteger.adapt)
sqlite3.register_converter("BIGINT", BigInteger.convert)
