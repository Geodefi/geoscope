"""
Defines the TimeDaemon class, a daemon for executing periodic actions at specified time intervals.

The TimeDaemon triggers a specified action at regular intervals defined in seconds, allowing for
flexible scheduling of recurring tasks.

Classes:
    TimeDaemon: Executes actions at user-defined intervals in seconds.
"""

from datetime import datetime

from src.classes import Daemon, Trigger
from src.globals import get_logger


class TimeDaemon(Daemon):
    """
    A Daemon that triggers provided actions at every specified interval in seconds.

    TimeDaemon executes the provided triggers at regular intervals specified by `interval`.

    Example:
        def action(current_time):
            print(f"Triggered at {current_time}")

        trigger = Trigger(action=action, name="TimeTrigger")
        time_daemon = TimeDaemon(interval=5, trigger=trigger, initial_delay=0)
        time_daemon.run()
        # To stop the daemon:
        # time_daemon.stop()

    Attributes:
        name (str): The name of the daemon used for logging purposes ("TIME_DAEMON").
    """

    name: str = "TIME_DAEMON"

    def __init__(self, interval: int, trigger: Trigger, initial_delay: int = 0) -> None:
        """
        Initialize a TimeDaemon instance.

        The daemon will execute triggers at regular intervals specified by the `interval` parameter.

        Args:
            interval (int): Time interval in seconds between trigger executions.
            trigger (Trigger): An initialized Trigger instance to be executed.
            initial_delay (int, optional): Initial delay before the first execution, in seconds.
                Defaults to 0.

        Raises:
            ValueError: If `interval` is not a positive integer.
            ValueError: If `initial_delay` is negative.
        """
        if not isinstance(interval, int) or interval <= 0:
            raise ValueError("The 'interval' must be a positive integer.")
        if not isinstance(initial_delay, int) or initial_delay < 0:
            raise ValueError("The 'initial_delay' must be a non-negative integer.")

        super().__init__(
            interval=interval,
            task=self.reflect,
            trigger=trigger,
            initial_delay=initial_delay,
        )

        get_logger().debug(f"Trigger '{trigger:^20}' is attached to {self.name}.")

    def reflect(self) -> datetime:
        """
        Return the current datetime to be used by the trigger function.

        This method is called at each interval to perform the necessary action.

        Returns:
            datetime: The current datetime.
        """
        current_time = datetime.now()
        get_logger().debug(f"{self.name} is triggering at {current_time}.")
        return current_time
