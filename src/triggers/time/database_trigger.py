import os
from datetime import datetime
from typing import Any

from src.classes import Database, Trigger
from src.exceptions import BackupError
from src.globals import get_config, get_logger
from src.globals.constants.config import CHAIN_NAME_FIELD, DB_BACKUP_DIR_FIELD, DB_BACKUP_KEEP_FIELD


class DatabaseTrigger(Trigger):
    """
    A trigger that performs regular backups of the database.

    This trigger initiates a backup of the current database file to a specified
    backup directory with a timestamped filename, ensuring data is regularly
    saved for recovery purposes.
    """

    name: str = "DATABASE"

    def __init__(self) -> None:
        """
        Initialize the DatabaseTrigger instance.

        Sets up the trigger with the `backup_database` action.
        """
        super().__init__(action=self.backup_database, name=self.name)
        db_name = get_config(field=CHAIN_NAME_FIELD)
        self.backup_keep = get_config(field=DB_BACKUP_KEEP_FIELD)
        self.backup_dir = os.path.join(get_config(field=DB_BACKUP_DIR_FIELD), db_name)

    def backup_database(self, *args: Any) -> None:
        """
        Perform a backup of the database and save it to a timestamped file.

        Creates a backup by copying the current database to a file with a unique
        timestamp in the filename, stored in the designated backup directory.
        """
        _datetime: datetime = args[0]
        timestamp: str = _datetime.strftime("%Y%m%d_%H%M%S")

        try:
            with Database() as db:
                db.backup(self.backup_dir, timestamp)

            with Database() as db:
                db.cleanup(self.backup_dir, self.backup_keep)

            get_logger().info(
                f"Database backup and cleanup is completed successfully: {self.backup_dir}"
            )

        except Exception as e:
            get_logger().error(f"Failure during backup process: {e}")
            raise BackupError("Failure during backup process") from e
