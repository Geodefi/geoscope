import os

import click

from src.classes import Database
from src.commands.utils.config import setup_config
from src.commands.utils.env import set_env_var
from src.exceptions import DatabaseBackupError
from src.globals import get_logger
from src.setup import setup
from src.utils.timestamp import is_valid_timestamp


def locate_backup(chain: str, backup_dir: str, timestamp: str) -> str:
    """
    Locate the backup file based on chain, backup directory, and timestamp.

    If timestamp is not provided, locates the latest backup file in the given directory.

    Args:
        chain (str): Name of the blockchain network.
        backup_dir (str): Directory where backups are stored.
        timestamp (str): Timestamp of the backup to restore. Can be a formatted filename or integer.
                         If None, the latest backup is used.

    Returns:
        str: Path to the backup file.

    Raises:
        FileNotFoundError: If the backup directory or file does not exist.
    """
    backup_subdir = os.path.join(backup_dir, chain)
    if not os.path.exists(backup_subdir):
        raise FileNotFoundError(f"Backup directory does not exist: {backup_subdir}")

    if timestamp is None:
        # Find the latest backup
        backup_files = [
            f for f in os.listdir(backup_subdir) if f.endswith(".db") and is_valid_timestamp(f[:-3])
        ]
        if not backup_files:
            raise FileNotFoundError(f"No backup files found in {backup_subdir}")
        backup_files.sort(reverse=True)  # Newest first
        backup_filename = backup_files[0]
    else:
        # Convert timestamp if necessary
        if timestamp.endswith(".db"):
            backup_filename = timestamp
        else:
            backup_filename = f"{timestamp}.db"

    backup_path = os.path.join(backup_subdir, backup_filename)
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup file does not exist: {backup_path}")

    return backup_path


def restore(chain: str, backup_path: str) -> None:
    """
    Restore the database for the specified chain from a backup file.

    Args:
        chain (str): Name of the blockchain network (e.g., 'holesky', 'ethereum').
        backup_path (str): Path to the backup file to restore.

    Raises:
        DatabaseBackupError: If an error occurs during the restore process.
        Exception: For any unexpected errors during the process.
    """
    try:
        get_logger().info(f"Restoring backup for {chain} from {backup_path}")
        with Database() as db:
            db.restore(backup_path)
        get_logger().info("Restore successful.")

    except DatabaseBackupError as e:
        get_logger().error(f"An error occurred during restore: {e}")
        get_logger().info("Restore failed.")

    # pylint: disable-next=broad-exception-caught
    except Exception as e:
        get_logger().error(f"An unexpected error occurred: {e}")
        get_logger().info("Restore failed.")


@click.option(
    "--traceback",
    is_flag=True,
    required=False,
    default=False,
    help="Will print the full Exception traceback. Useful for developers.",
)
@click.option(
    "--backup-dir",
    envvar="GEOSCOPE_BACKUP_DIR",
    type=click.Path(),
    help="Directory where the backup will be stored.",
)
@click.option(
    "--timestamp",
    required=False,
    type=click.STRING,
    help="Timestamp of the backup to restore (formatted filename or integer)."
    "If not provided, the latest backup will be automatically located.",
)
@click.option(
    "--file",
    "backup_file",
    required=False,
    type=click.STRING,
    help="Path to the backup file to restore.",
)
@click.option(
    "--main-dir",
    envvar="GEOSCOPE_MAIN_DIR",
    type=click.STRING,
    required=False,
    is_eager=True,
    callback=setup_config,
    default=".geoscope",
    help="Relative path for the directory that will be used to store data. Default is .geoscope",
)
@click.option(
    "--chain",
    envvar="GEOSCOPE_CHAIN",
    type=click.Choice(["holesky", "ethereum"]),
    required=True,
    is_eager=True,
    default="holesky",
    callback=set_env_var,
    prompt="You forgot to specify the chain:",
    help="Network name, such as 'holesky' or 'ethereum' etc.",
)
@click.command(
    help="Restore the database for the given chain from a backup. \
    Either the file path or backup directory and a timestamp should be specified"
)
def main(
    backup_dir: str, timestamp: str, backup_file: str, chain: str, main_dir: str, traceback: bool
) -> None:
    """
    Restore the database for the specified chain from a backup.

    User must provide either '--file' OR both '--backup-dir' and '--timestamp'.

    Args:
        backup_dir (str): Directory where the backups are stored.
        timestamp (str): Timestamp of the backup to restore (formatted filename or integer).
        backup_file (str): Path to the backup file to restore.
        chain (str): Name of the chain. 'holesky', 'ethereum', etc.
        traceback (bool): Will print the full Exception traceback. Useful for developers.

    """
    try:
        setup(main_dir=main_dir, setup_logger=True, setup_sdk=False, setup_db=True, verify=False)

        # Validate options
        if backup_file and (backup_dir or timestamp):
            get_logger().error(
                "Cannot provide both --file and, --backup-dir + --timestamp options."
            )
            get_logger().error("Restore failed.")
            return
        elif backup_file:
            backup_path = backup_file
        elif backup_dir:
            try:
                backup_path = locate_backup(chain, backup_dir, timestamp)
            except FileNotFoundError as e:
                get_logger().error(e)
                get_logger().error("Restore failed.")
                return
        else:
            get_logger().error(
                "Provide the path for the backup directory to restore from the latest backup."
                "If you want to restore from a specific file, exit and provide --file flag."
            )
            get_logger().error("Restore failed.")
            return

        if not os.path.exists(backup_path):
            get_logger().error(f"Backup file does not exist: {backup_path}")
            get_logger().error("Restore failed.")
            return

        restore(chain, backup_path)

    # pylint: disable-next=broad-exception-caught
    except Exception as e:
        get_logger().error(str(e))
        get_logger().error("Could not initiate geoscope")
        get_logger().info("Exiting...")

        if traceback:
            raise e
