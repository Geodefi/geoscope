import os
from datetime import datetime

import click

from src.classes import Database
from src.commands.utils.config import setup_config
from src.commands.utils.env import set_env_var
from src.exceptions import CleanupError, DatabaseBackupError
from src.globals import get_logger
from src.setup import setup


def backup_cleanup(chain: str, backup_dir: str, keep: int) -> None:
    """
    Perform a manual database backup for the specified chain and clean up old backups.

    Creates a backup of the database associated with the given chain, storing it in the
    specified backup directory. Retains only the most recent backups, deleting older ones
    to manage disk space.

    Args:
        chain (str): Name of the blockchain network (e.g., 'holesky', 'ethereum').
        backup_dir (str): Directory where backups are stored.
        keep (int): Number of backups to keep; older backups will be deleted if exceeded.

    Raises:
        DatabaseBackupError: If an error occurs during the backup process.
        CleanupError: If an error occurs during the cleanup of old backups.
        Exception: For any unexpected errors during the process.
    """
    # Ensure backup directory exists
    backup_subdir = os.path.join(backup_dir, chain)
    try:
        _datetime: datetime = datetime.now()
        timestamp: str = _datetime.strftime("%Y%m%d_%H%M%S")

        get_logger().info(f"Starting database backup for  {chain} on {timestamp}")
        with Database() as db:
            db.backup(backup_subdir, timestamp)

        if keep:
            with Database() as db:
                db.cleanup(backup_subdir, keep)
        get_logger().info("Backup successfull.")

    except (DatabaseBackupError, CleanupError) as e:
        get_logger().error(f"An error occurred during backup: {e}")
        get_logger().error("Restore failed.")

    # pylint: disable-next=broad-exception-caught
    except Exception as e:
        get_logger().error(f"An unexpected error occurred: {e}")
        get_logger().error("Restore failed.")


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
    required=True,
    type=click.Path(),
    help="Directory where the backup will be stored.",
)
@click.option(
    "--keep",
    envvar="GEOSCOPE_BACKUP_KEEP",
    required=False,
    type=click.IntRange(0, 10),
    default=None,
    help="Optional. Number of backups to keep. Older backups will be deleted if exceeded.",
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
@click.command(help="Perform a manual backup for the database on the given chain.")
def main(backup_dir: str, keep: int, chain: str, main_dir: str, traceback: bool) -> None:
    """
    Perform a manual backup for the database on the specified chain.

    Args:
        backup_dir (str): Directory where the backup will be stored.
        backup_keep (int): Number of backups to keep. Older backups will be deleted if exceeded.
        chain (str): Name of the chain. 'holesky', 'ethereum' etc.
        main_dir (str): Path to the main directory for data storage.
        traceback (bool): Will print the full Exception traceback. Useful for developers.
    """
    try:
        setup(main_dir=main_dir, setup_logger=True, setup_sdk=False, setup_db=True, verify=False)
        backup_cleanup(chain, backup_dir, keep)

    # pylint: disable-next=broad-exception-caught
    except Exception as e:
        get_logger().error(str(e))
        get_logger().error("Could not initiate geoscope")
        get_logger().info("Exiting...")

        if traceback:
            raise e
