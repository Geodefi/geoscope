"""
Database Management Module for Geoscope Application.

Database class is a helper for managing SQLite database connections
using context managers. It facilitates executing SQL commands safely and handling transactions
with ease.
"""

import os
import re
import shutil
import sqlite3 as sql
from threading import RLock
from types import TracebackType
from typing import Any

from tqdm import tqdm

from src.exceptions import CleanupError, DatabaseBackupError, DatabaseError
from src.globals import get_config, get_logger
from src.globals.constants.config import CHAIN_NAME_FIELD, DB_DIR_FIELD, MAIN_DIR_FIELD
from src.globals.constants.database import SQL_CONNECTION_TIMEOUT
from src.utils.progress_bar import progress_bar
from src.utils.timestamp import is_valid_timestamp


class Database:
    """A helper class for managing SQLite database connections using context managers.

    Facilitates executing SQL commands safely, handling transactions, and ensuring
    proper resource cleanup. It is designed to simplify database interactions for other classes
    within the Geoscope application.

    Example:
        .. code-block:: python

            from database_module import Database

            def create_table():
                with Database() as db:
                    db.execute(
                        f'''
                        CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT NOT NULL UNIQUE,
                            email TEXT NOT NULL UNIQUE
                        )
                        '''
                    )

            def add_users(username: str, email: str):
                with Database() as db:
                    db.executemany(
                        'INSERT INTO users (username, email) VALUES (?, ?)',
                        users
                    )

            def read_all_users() -> list[dict[str, Any] | None]:
                with Database() as db:
                    db.execute('SELECT * FROM users')
                    return db.fetchall()

    Attributes:
        __db_ext (str): Extension of the database file for the current instance.
        db_name (str): Name of the database file for the current instance.
        connection (sqlite3.Connection): Connection object to the database file.
        cursor (sqlite3.Cursor): Cursor object to execute SQL commands.
        _lock (threading.RLock): A lock to manage thread-safe operations.
    """

    __db_ext: str = ".db"

    def __init__(self, db_name: str = "") -> None:
        """
        Initializes a Database instance. Establishes a connection to the SQLite database and
        prepares the cursor for executing SQL commands.

        Args:
            db_name (str): Name of the database file. Defaults to the chain name from configuration.
                Defaults to the chain name if not provided.


        Raises:
            DatabaseError: If an error occurs while connecting to the database.
        """

        _db_name: str = self.sanitize_db_name(db_name or get_config(field=CHAIN_NAME_FIELD))

        self.db_path: str = os.path.join(
            get_config(field=MAIN_DIR_FIELD), get_config(field=DB_DIR_FIELD)
        )
        os.makedirs(self.db_path, exist_ok=True)

        self.conn_path: str = os.path.join(self.db_path, _db_name + self.__db_ext)
        self.progress_bar: tqdm | None = None
        self.last_remaining: int = 0

        try:
            self.connection: sql.Connection = sql.connect(
                self.conn_path,
                timeout=SQL_CONNECTION_TIMEOUT,
                detect_types=sql.PARSE_DECLTYPES,  # <-- crucial for custom converters
            )
            self._cursor: sql.Cursor | None = None
        except sql.Error as e:
            get_logger().debug(f"SQL version: {sql.version}")
            get_logger().debug(f"sqlite version: {sql.sqlite_version}")
            raise DatabaseError(
                f"Error while connecting to the database with database path {self.conn_path}"
            ) from e
        except Exception as e:
            get_logger().error(f"Unexpected error while connecting to the database: {e}")
            raise DatabaseError(
                f"Unexpected error while connecting to the database with path {self.conn_path}"
            ) from e

        self._lock: RLock = RLock()

    @property
    def cursor(self) -> sql.Cursor:
        """Get the database cursor, creating it if it doesn't exist."""
        if self._cursor is None:
            self._cursor = self.connection.cursor()
        return self._cursor

    def __enter__(self) -> "Database":
        """
        Enter the runtime context related to the Database object.

        Returns:
            Database: The Database instance itself.
        """
        return self

    def __exit__(
        self,
        ext_type: BaseException | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """
        Exit the runtime context and close the database connection.

        Commits the transaction if no exception occurred, otherwise rolls back.

        Args:
            exc_type (Type[BaseException] | None): Type of exception, if an exception was raised.
            exc_value (BaseException | None): Exception object, if an exception was raised.
            traceback (TracebackType | None): Traceback object, if an exception was raised.
        """

        try:
            if exc_value:
                self.connection.rollback()
                get_logger().debug("Transaction rolled back due to an exception.")
            else:
                self.connection.commit()
        except sql.Error as e:
            get_logger().error("Failed to commit or rollback the transaction.")
            raise DatabaseError("Failed to finalize the transaction...") from e
        finally:
            self.connection.close()

    def execute(
        self, query: str, params: dict[str, Any] | list[Any] | tuple[Any, ...] | None = None
    ) -> None:
        """
        Execute a SQL query with optional named parameters.

        Args:
            query (str): The SQL query to execute.
            params (dict[str, Any] | list[Any] | tuple[Any, ...] | None,  optional):
                Parameters to substitute into the query.
                Can be a dictionary for named parameters or a list/tuple for positional parameters.
                Defaults to None.

        Raises:
            DatabaseError: If the query execution fails.
        """
        with self._lock:
            try:
                if params is None:
                    self.cursor.execute(query)
                else:
                    self.cursor.execute(query, params)
            except sql.Error as e:
                get_logger().error(f"Failed to execute query: {query} with params: {params}: {e}")
                raise DatabaseError("Failed to execute query.") from e

    def executemany(self, query: str, params_list: list[dict[str, Any]]) -> None:
        """
        Execute a parameterized SQL query against all parameter dictionaries provided.

        Args:
            query (str): The SQL query to execute.
            params_list (list[dict[str, Any]]): A list of named parameters.

        Raises:
            DatabaseError: If the query execution fails.
        """
        with self._lock:
            try:
                self.cursor.executemany(query, params_list)
            except sql.Error as e:
                get_logger().error(
                    f"Failed to execute many queries: {query} with params: {params_list}: {e}"
                )
                raise DatabaseError("Failed to execute many queries.") from e

    def fetchone(self) -> tuple[Any, ...] | None:
        """
        Fetch the next row of a query result.

        Returns:
            tuple[Any, ...] | None: Contains the fetched row. None if no more available rows.

        Raises:
            DatabaseError: If fetching the result fails.
        """
        try:
            result = self.cursor.fetchone()
            return result
        except sql.Error as e:
            get_logger().error(f"Failed to fetch one result: {e}")
            raise DatabaseError("Failed to fetch one result.") from e

    def fetchall(self) -> list[tuple[Any, ...]]:
        """
        Fetch all (remaining) rows of a query result.

        Returns:
            list[tuple[str, Any] | None]: A list of dicts containing the fetched rows.

        Raises:
            DatabaseError: If fetching the results fails.
        """
        try:
            results = self.cursor.fetchall()
            return results
        except sql.Error as e:
            get_logger().error(f"Failed to fetch all results: {e}")
            raise DatabaseError("Failed to fetch all results.") from e

    @staticmethod
    def sanitize_db_name(name: str) -> str:
        """
        Sanitize the database name to include only alphanumeric characters, underscores, and hyphens

        Args:
            name (str): The original database name.

        Returns:
            str: The sanitized database name.
        """
        return re.sub(r"[^A-Za-z0-9_\-]", "_", name)

    def backup(self, backup_dir: str, timestamp: str | int) -> None:
        """
        Create a backup of the current SQLite database.

        Copies the current database file to the specified backup path using SQLite's backup API.

        Args:
            backup_dir (str): The folder path where the backup will be stored.
            timestamp (str|int): Timestamp will be used as the file name.

        Raises:
            DatabaseError: If the backup process fails.
        """
        with self._lock:
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, f"{timestamp}.db")
            try:
                backup_conn = sql.connect(
                    backup_path,
                    timeout=SQL_CONNECTION_TIMEOUT,
                    check_same_thread=False,  # Allow connection across threads if necessary
                )
                with backup_conn:
                    self.connection.backup(backup_conn, pages=1, progress=self.progress)
                backup_conn.close()
                get_logger().info(f"Database backed up successfully to {backup_path}.")
            except sql.Error as e:
                get_logger().error(f"Failed to backup database to {backup_path}: {e}")
                raise DatabaseBackupError(f"Failed to backup database to {backup_path}.") from e
            except Exception as e:
                get_logger().error(f"Unexpected error during backup: {e}")
                raise DatabaseBackupError("Unexpected error during database backup.") from e

    def restore(self, backup_path: str) -> None:
        """
        Restore the SQLite database from a backup file.

        This method replaces the current database with the backup located at the specified path.

        Args:
            backup_path (str): The file path of the backup to restore from.

        Raises:
            DatabaseError: If the restoration process fails.
            DatabaseBackupError: If expected backup path does not exist.
        """
        with self._lock:
            if not os.path.exists(backup_path):
                raise DatabaseBackupError(f"Backup path does not exist: {backup_path}")
            try:
                self.connection.close()
                shutil.copyfile(
                    backup_path,
                    self.conn_path,
                )
                self.connection = sql.connect(
                    self.conn_path,
                    timeout=SQL_CONNECTION_TIMEOUT,
                )
                self._cursor = None
                get_logger().info(f"Database restored successfully from {backup_path}.")
            except sql.Error as e:
                get_logger().error(f"Failed to restore database from {backup_path}: {e}")
                raise DatabaseBackupError(f"Failed to restore database from {backup_path}.") from e
            except Exception as e:
                get_logger().error(f"Unexpected error during restoration: {e}")
                raise DatabaseBackupError("Unexpected error during database restoration.") from e

    @staticmethod
    def cleanup(backup_dir: str, backup_keep: int) -> None:
        """
        Deletes oldest backup files in 'backup_dir', keeping only the latest 'backup_keep' backups.

        Scans 'backup_dir' for timestamped '.db' files matching the expected naming convention.
        Older backups are deleted to manage disk space and keep the directory organized.

        Args:
            backup_dir (str): Path to the directory where backup files are stored.
            backup_keep (int): Maximum number of backup files to retain.

        Raises:
            CleanupError: If an error occurs while deleting old backup files.
            DatabaseBackupError: If expected backup path does not exist.

        Notes:
            - Backup files must end with '.db' and have a valid timestamp in '%Y%m%d_%H%M%S' format.
            - Does nothing if the number of backups is less than or equal to 'backup_keep'.
            - Backups are sorted by timestamps derived from filenames; oldest backups are deleted.
        """
        if not os.path.exists(backup_dir):
            raise DatabaseBackupError(f"Backup path does not exist: {backup_dir}")
        # List all backup files in the backup subdirectory
        backup_files = [
            f for f in os.listdir(backup_dir) if f.endswith(".db") and is_valid_timestamp(f[:-3])
        ]
        # If the number of backups is less than or equal to backup_keep, do nothing
        if len(backup_files) <= backup_keep:
            return

        # Sort the backup files by their timestamp (oldest first)
        backup_files.sort()

        # Calculate how many backups need to be deleted
        num_files_to_delete = len(backup_files) - backup_keep

        # Delete the oldest backups
        for i in range(num_files_to_delete):
            file_to_delete = os.path.join(backup_dir, backup_files[i])
            try:
                os.remove(file_to_delete)
                get_logger().info(f"Deleted old backup file: {file_to_delete}")
            except Exception as e:
                get_logger().error(f"Failed to delete old backup file {file_to_delete}")
                raise CleanupError(f"Failed to delete old backup file {file_to_delete}") from e

    # pylint: disable-next=unused-argument
    def progress(self, status: int, remaining: int, total: int) -> None:
        """
        Callback function for SQLite backup progress.

        Updates a progress bar to reflect the backup progress of the database.

        Args:
            status (int): The current status code of the backup operation.
            remaining (int): The number of remaining pages to be backed up.
            total (int): The total number of pages to back up.
        """
        if self.progress_bar is None:
            self.progress_bar = progress_bar(
                total=total,
                desc="Backing up database",
                unit="pages",
            )
            self.last_remaining = total

        self.progress_bar.update(self.last_remaining - remaining)
        self.last_remaining = remaining

        if remaining == 0:
            self.progress_bar.clear()  # Ensure bar is cleared
            self.progress_bar.close()  # Ensure bar is closed
            self.progress_bar = None
