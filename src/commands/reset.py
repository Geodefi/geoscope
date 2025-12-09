import os

import click

from src.classes import Database
from src.commands.utils.config import setup_config
from src.commands.utils.env import set_env_var
from src.globals import get_config, get_logger
from src.globals.constants.config import LOGGER_DIR_FIELD
from src.globals.constants.database import MERKLES_TABLE_KEY, SLOTS_TABLE_KEY
from src.globals.schemas.database import DATABASE_SCHEMA
from src.setup import setup
from src.setup.database import reinitialize_db_tables
from src.utils.progress_bar import time_bar


def reset(
    logs: bool, database: tuple[str], backups: str, force: bool, main_dir: str, chain: str
) -> None:
    """
    Reset databases, logs, or backups for the specified chain.

    Args:
        logs (bool): If True, clear logs in main_dir/logger_dir folder.
        database (str): Comma-separated list of databases to reset.
        force (bool): If True, bypass confirmation prompts and time delays.
        backups (str): Path to the backups folder to remove backups from.
        main_dir (str): Path to the main directory for data storage.

    """
    if not any([logs, database, backups]):
        get_logger().error(
            "No action specified. Provide at least one option to reset: logs, database, backups"
        )
        return

    if logs:
        # Determine logger path
        logger_dir: str = os.path.join(main_dir, get_config(field=LOGGER_DIR_FIELD))
        if os.path.exists(logger_dir):
            if not force:
                click.confirm(
                    f"Delete all log files for {chain} chain in {logger_dir}?", abort=True
                )
                time_bar(5, desc="CTRL+C to abort")

            clear_logs(logger_dir, chain)
        else:
            get_logger().warning(f"Logs directory {logger_dir} does not exist.")

    if backups:
        backups_dir = os.path.join(backups, chain)
        if not os.listdir(backups_dir):
            get_logger().error(f"No backups found in {backups_dir}. Nothing to delete.")
        else:
            if not force:
                click.confirm(f"Delete all backups for {chain} chain in {backups_dir}?", abort=True)
                time_bar(duration=5, desc="CTRL+C to abort")
            clear_backups(backups_dir)

    if database:
        tables_list = list(database)
        if "all" in tables_list:
            # Reset all databases
            tables_list = [*DATABASE_SCHEMA.keys()]
        clear_database(tables_list, force)


def clear_logs(logs_dir: str, chain: str) -> None:
    """
    Delete log files in the specified directory that start with the chain name.

    Args:
        logs_dir (str): Path to the logs directory.
        chain (str): Name of the chain (e.g., 'holesky', 'ethereum').

    Raises:
        Exception: If any log file cannot be deleted.
    """
    deleted_files = []
    try:
        get_logger().info(f"Deleting all log files for chain:{chain}")
        for filename in os.listdir(logs_dir):
            if filename.startswith(f"{chain}."):
                file_path = os.path.join(logs_dir, filename)
                os.remove(file_path)
                deleted_files.append(filename)
        if deleted_files:
            get_logger().info(f"Deleted log files: {', '.join(deleted_files)}")
        else:
            get_logger().error(f"No log files starting with '{chain}.' found in {logs_dir}")

    # pylint: disable-next=broad-exception-caught
    except Exception as e:
        get_logger().error(f"Failed to delete log files in {logs_dir}: {e}")
        raise


def clear_backups(backups_dir: str) -> None:
    """
    Delete all backups in the specified directory.

    Args:
        backups_dir (str): Path to the backups directory.

    Raises:
        SystemExit: If the backups directory cannot be deleted.
    """
    try:
        with Database() as db:
            db.cleanup(backups_dir, 0)
        get_logger().info(f"All backups in {backups_dir} have been deleted.")
    # pylint: disable-next=broad-exception-caught
    except Exception as e:
        get_logger().error(f"Failed to delete backups in {backups_dir}: {e}")


def clear_database(tables: list[str], force: bool) -> None:
    """
    Drop specified database tables.

    Args:
        databases (list[str]): List of database tables to delete.
        force (bool): If True, bypass confirmation prompts and delays.

    """
    try:
        if not force:
            # Warn about special tables
            if SLOTS_TABLE_KEY in tables:
                get_logger().warning(
                    f"Deleting {SLOTS_TABLE_KEY} table will require reprocessing of all slots \
                        from start slot, which is very time consuming."
                )
                click.confirm(f"Drop {SLOTS_TABLE_KEY} table?", abort=True)

            if MERKLES_TABLE_KEY in tables:
                get_logger().warning(
                    f"Deleting {MERKLES_TABLE_KEY} table will remove all Merkle Trees."
                    "This action can not be reverted, without restoring from a backup!"
                )
                click.confirm(f"Drop {MERKLES_TABLE_KEY} table?", abort=True)

            time_bar(duration=5, desc="CTRL+C to abort")

        reinitialize_db_tables(*tables)

    # pylint: disable-next=broad-exception-caught
    except Exception as e:
        get_logger().error(f"Failed to drop table: {e}")


@click.option(
    "--traceback",
    is_flag=True,
    required=False,
    default=False,
    help="Will print the full Exception traceback. Useful for developers.",
)
@click.option(
    "--logs",
    required=False,
    is_flag=True,
    help="Clear logs in main_dir/logger_dir folder.",
)
@click.option(
    "--db",
    "database",
    required=False,
    type=click.Choice(["all", *DATABASE_SCHEMA.keys()]),
    multiple=True,
    help=f"""Database Tables to drop.\n 'all' drops all tables including slots and merkles.
    Dropping {SLOTS_TABLE_KEY} will require reprocessing all slots from start, which is very time consuming.\n\
    Dropping {MERKLES_TABLE_KEY} can not be reverted without restoring from a backup.
    """,
)
@click.option(
    "--backups",
    type=click.Path(exists=True, file_okay=False),
    help="Path to the backups folder to remove backups from.",
)
@click.option(
    "--force", is_flag=True, is_eager=True, help="Bypass all confirmation prompts and time delays."
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
@click.command(help="Reset databases, logs, or backups for the specified chain.")
def main(
    logs: bool,
    database: tuple[str],
    backups: str,
    force: bool,
    chain: str,
    main_dir: str,
    traceback: bool,
) -> None:
    """
    Reset databases, logs, or backups for the specified chain.

    Args:
        logs (bool): If True, clear logs in main_dir/logger_dir folder.
        database (str): Comma-separated list of databases to reset.
        backups (str): Path to the backups folder to remove backups from.
        force (bool): If True, bypass confirmation prompts and time delays.
        chain (str): Name of the chain ('holesky' or 'ethereum').
        main_dir (str): Path to the main directory for data storage.
        traceback (bool): Will print the full Exception traceback. Useful for developers.
    """
    try:
        setup(main_dir=main_dir, setup_logger=True, setup_sdk=False, setup_db=True, verify=False)
        reset(
            logs=logs,
            database=database,
            backups=backups,
            force=force,
            main_dir=main_dir,
            chain=chain,
        )

    # pylint: disable-next=broad-exception-caught
    except Exception as e:
        get_logger().error(str(e))
        get_logger().error("Could not initiate geoscope")
        get_logger().info("Exiting...")

        if traceback:
            raise e
