class DatabaseError(Exception):
    """Exception raised for errors related with Database actions."""


class DatabaseMismatchError(DatabaseError):
    """Exception raised for errors related with Database mismatches."""


class DatabaseBackupError(Exception):
    """Exception raised when a database backup fails."""
