from src.classes import Daemon
from src.daemons import SlotDaemon, TimeDaemon
from src.exceptions import DaemonInitializationError
from src.globals import get_config, get_logger
from src.globals.constants.config import DB_BACKUP_INTERVAL_FIELD, STRATEGY_SLOT_PERIOD_FIELD
from src.triggers import BeaconTrigger, DatabaseTrigger


def run_slot_daemon(slot_period: int) -> None:
    """
    Initialize and run the SlotDaemon for handling slot-based events.

    Sets up and starts the SlotDaemon using the BeaconTrigger and slot period
    from the configuration.

    Raises:
        DaemonInitializationError: If there is an issue initializing or running the SlotDaemon.
    """
    try:
        # Initialize BeaconTrigger
        beacon_trigger: BeaconTrigger = BeaconTrigger()
        get_logger().debug("BeaconTrigger initialized.")

        # Get slot period from configuration
        get_logger().info(f"Slot period for SlotDaemon: {slot_period} slots")

        # Create and run SlotDaemon
        slot_daemon: SlotDaemon = SlotDaemon(trigger=beacon_trigger, slot_period=slot_period)
        get_logger().debug("Starting SlotDaemon...")
        slot_daemon.run()
        get_logger().info("SlotDaemon is running.")

    except Exception as e:
        get_logger().error(f"Failed to initialize or run SlotDaemon: {e}")
        raise DaemonInitializationError("Failed to initialize or run SlotDaemon.") from e


def run_database_daemon(backup_interval: int) -> None:
    """
    Initialize and run the TimeDaemon for handling database backups.

    Sets up and starts the TimeDaemon using the DatabaseTrigger and backup interval
    from the configuration.

    Raises:
        DaemonInitializationError: If there is an issue initializing or running the DatabaseDaemon.
    """
    try:
        # Initialize DatabaseTrigger
        database_trigger: DatabaseTrigger = DatabaseTrigger()
        get_logger().debug("DatabaseTrigger initialized.")

        # Get backup interval from configuration
        get_logger().info(f"Backup interval for DatabaseDaemon: {backup_interval} seconds")

        # Create and run TimeDaemon
        database_daemon: TimeDaemon = TimeDaemon(
            interval=backup_interval,
            trigger=database_trigger,
            initial_delay=backup_interval,
        )
        get_logger().debug("Starting DatabaseTrigger...")
        database_daemon.run()
        get_logger().info("DatabaseDaemon is running.")

    except Exception as e:
        get_logger().error(f"Failed to initialize or run DatabaseDaemon: {e}")
        raise DaemonInitializationError("Failed to initialize or run DatabaseDaemon.") from e


def run_daemons() -> None:
    """
    Initialize and run all daemon processes for the Geoscope application.

    Calls individual functions to start the SlotDaemon and DatabaseDaemon,
    and registers shutdown handlers.

    Raises:
        DaemonInitializationError: If there is an issue initializing or running the daemons.
    """
    try:
        get_logger().info("Initializing daemons...")

        slot_period = get_config(field=STRATEGY_SLOT_PERIOD_FIELD)
        backup_interval = get_config(field=DB_BACKUP_INTERVAL_FIELD)

        # Run individual daemons
        run_slot_daemon(slot_period=slot_period)
        run_database_daemon(backup_interval=backup_interval)

        # Register shutdown handlers
        Daemon.register_shutdown_handlers()

        get_logger().info("All daemons are running.")

    except DaemonInitializationError as e:
        get_logger().error(f"Daemon initialization error: {e}")
        raise e
    except Exception as e:
        get_logger().error(f"Unexpected error during daemon initialization: {e}")
        raise DaemonInitializationError("Failed to initialize or run daemons.") from e
