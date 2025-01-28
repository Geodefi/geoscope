"""
Daemon Management Module for Geoscope.

This module defines the Daemon class, which handles the execution of background tasks
at specified intervals. It manages task execution, trigger processing, and handles
various exceptions to ensure robust daemon operations.
"""

import signal
import time
from threading import Event, Lock, Thread
from types import FrameType
from typing import Any, Callable

from web3.exceptions import TimeExhausted

from src.classes.trigger import Trigger
from src.exceptions import (
    CallFailedError,
    DaemonError,
    EmailError,
    EventFetchingError,
    HighGasError,
)
from src.globals import get_logger
from src.utils.notify import send_email

# Define a global shutdown event
shutdown_event = Event()


# pylint: disable-next=unused-argument
def handle_shutdown_signal(signum: int, frame: FrameType | None) -> None:
    """
    Handle shutdown signals to initiate a graceful shutdown.

    Args:
        signum (int): The signal number.
        frame (FrameType): The current stack frame.
    """
    get_logger().warning("Shutdown signal is received. Initiating graceful shutdown...")
    shutdown_event.set()


class Daemon:
    """
    A daemon that repeatedly executes a specific task at a given interval.

    Daemons use a single thread to run a background loop that executes the provided task
    and processes triggers on every iteration.

    Example:
        .. code-block:: python

            def print_time():
                print(datetime.datetime.now())

            def quick_run():
                trigger_instance = Trigger(...)
                daemon = Daemon(interval=3, task=print_time, trigger=trigger_instance)
                daemon.run()
                sleep(10)  # Let it run for a while
                daemon.stop()

            quick_run()

    Attributes:
        _interval (int): Time duration between two task executions in seconds.
        _initial_delay (int): Initial delay before starting the loop in seconds.
        _task (Callable[..., Any]): The task to be executed after every interval.
        _worker (Thread): Thread object running the daemon loop.
        trigger (Trigger): An initialized Trigger instance.
        _lock (Lock): A lock to manage thread-safe operations.
        stop_flag (Event): Event flag indicating the daemon should stop.
    """

    def __init__(
        self,
        interval: int,
        task: Callable[..., Any],
        trigger: Trigger,
        initial_delay: int = 0,
    ) -> None:
        """
        Initialize a Daemon instance.

        The daemon will execute the provided task at the specified interval.

        Args:
            interval (int): Time duration between two task executions, in seconds.
            task (Callable[..., Any]): The task function to execute on each interval.
            trigger (Trigger): A Trigger instance already initialized with a registered action.
            initial_delay (int, optional): Initial delay before starting the loop in seconds.
                Defaults to 0.

        Raises:
            ValueError: If interval or initial_delay are not positive integers.
            TypeError: If trigger is not an instance of Trigger.
        """
        if not isinstance(interval, int) or interval <= 0:
            raise ValueError("Interval must be a positive integer.")
        if not isinstance(initial_delay, int) or initial_delay < 0:
            raise ValueError("Initial delay must be a non-negative integer.")
        if not isinstance(trigger, Trigger):
            raise TypeError("Given trigger is not an instance of Trigger.")

        get_logger().debug(
            f"Initializing a Daemon object. Interval: {interval}s, "
            f"Trigger: {trigger:^20}, Initial Delay: {initial_delay}s"
        )
        self.__set_task(task)
        self.__set_interval(interval)
        self.__set_initial_delay(initial_delay)
        self.__set_trigger(trigger)

        self._worker: Thread = Thread(name=str(trigger), target=self.__loop)
        self._shutdown_monitor: Thread = Thread(
            name="Shutdown_Monitor", target=self.__check_shutdown
        )
        self._lock = Lock()
        self.stop_flag: Event = Event()
        get_logger().debug(f"Initialized a Daemon for: {trigger:^20}.")

    @property
    def interval(self) -> int:
        """Get the waiting period between task executions in seconds.

        Returns:
            int: Waiting period in seconds.
        """
        return self._interval

    @property
    def initial_delay(self) -> int:
        """Get the initial delay before the daemon starts looping in seconds.

        Returns:
            int: Initial delay in seconds.
        """
        return self._initial_delay

    def __set_interval(self, interval: int) -> None:
        """Set the waiting period between task executions.

        Args:
            interval (int): New waiting period in seconds.
        """
        self._interval: int = interval

    def __set_initial_delay(self, initial_delay: int) -> None:
        """Set the initial delay before the daemon starts looping.

        Args:
            initial_delay (int): New initial delay in seconds.
        """
        self._initial_delay: int = initial_delay

    def __set_task(self, task: Callable[..., Any]) -> None:
        """Set the task to be executed by the daemon.

        Tasks should return a dictionary of effects to be checked by the trigger.

        Args:
            task (Callable[..., Any]): New task function to be executed after every interval.
        """
        self._task: Callable[..., Any] = task

    def __set_trigger(self, trigger: Trigger) -> None:
        """Set the trigger instance for the daemon.

        Args:
            trigger (Trigger): An initialized Trigger instance.
        """
        self.trigger: Trigger = trigger

    def __loop(self) -> None:
        """
        Run the daemon loop, executing the task and processing triggers on every iteration.

        The loop runs continuously at the specified interval until either the `stop_flag` is set
        (via the `stop` method) or the global `shutdown_event` is set (via a shutdown signal).
        If the task raises an exception, the daemon handles it accordingly, possibly sending
        notifications and initiating shutdowns.

        Raises:
            DaemonError: Raised if the daemon stops due to an unhandled exception.
        """
        self.__graceful_delay(self._initial_delay)

        while not self.stop_flag.wait(self.interval):
            try:
                result = self._task()

                if result:
                    self.trigger.process(result)

            # TODO:(5) Is all exception handling done and verified here?
            except (TimeExhausted, CallFailedError):
                get_logger().warning(
                    f"One of the calls failed for {self.trigger:^20}. "
                    "Continuing but may need to be checked in case of a problem."
                )
                try:
                    send_email(
                        "Transaction Failed",
                        "A Portal transaction has failed or could not be called for some reason. "
                        "Operations will continue as usual, but an investigation is suggested.",
                    )
                except EmailError:
                    get_logger().warning(
                        "Unable to communicate with the owners. Continuing without assistance."
                    )
            except HighGasError as e:
                get_logger().error(str(e))
                get_logger().warning(
                    f"High gas detected for {self.trigger:^20}. "
                    "Continuing but may need to be checked in case of a problem."
                )
                try:
                    send_email(
                        "High Gas Alert",
                        "The on-chain gas API reported that gas prices have surpassed \
                            the maximum setting.",
                        dont_notify_devs=True,
                    )
                except EmailError:
                    get_logger().warning(
                        "Unable to communicate with the owners. Continuing without assistance."
                    )
            except EventFetchingError as e:
                get_logger().error(str(e))
                try:
                    send_email(
                        "Event Fetching Error",
                        "There was an issue while fetching an event from the chain. "
                        "Geoscope will continue trying, but manual investigation is recommended.",
                        dont_notify_devs=True,
                    )
                except EmailError:
                    get_logger().warning(
                        "Unable to communicate with the owners. Continuing without assistance."
                    )
                self.stop_flag.set()

            # pylint: disable-next=broad-exception-caught
            except Exception as e:
                get_logger().exception(
                    f"Stopping Geoscope due to unhandled exception in Daemon for: \
                        {self.trigger:^20}"
                )
                try:
                    send_email(
                        "Geoscope Stopped",
                        "All daemons have stopped, and the script has exited. \
                            Please investigate the issue.",
                    )
                except EmailError:
                    get_logger().warning("Could not send email while exiting Geoscope.")

                shutdown_event.set()

    def __check_shutdown(self) -> None:
        """Monitor shutdown_event and propagate it to stop_flag"""
        while not self.stop_flag.is_set():
            if shutdown_event.wait(1):  # Check every second
                self.stop_flag.set()
                break

    def __graceful_delay(self, seconds: int) -> bool:
        """
        Delay execution for the specified number of seconds, checking stop_flag every second.
        Returns True if completed successfully, False if interrupted by stop_flag.
        """
        if seconds <= 0:
            return True

        end_time = time.time() + seconds

        while time.time() < end_time:
            if self.stop_flag.is_set():
                return False
            time.sleep(min(1, end_time - time.time()))

        return True

    def run(self) -> None:
        """
        Start the daemon loop.

        Raises:
            DaemonError: Raised if the daemon is already running.
        """
        with self._lock:
            if self._worker.is_alive():
                get_logger().error("Daemon is already running.")
                raise DaemonError("Daemon is already running.")

            self._worker.start()
            self._shutdown_monitor.start()
            get_logger().info(
                f"Daemon for {self.trigger:^20} will run every {self.interval} seconds."
            )

    def stop(self) -> None:
        """
        Stop the daemon loop gracefully.

        Raises:
            DaemonError: Raised if the daemon is already stopped.
        """
        with self._lock:
            if not self._worker.is_alive():
                get_logger().error("Daemon is already stopped.")
                raise DaemonError("Daemon is already stopped.")

            self.stop_flag.set()
            self._worker.join()
            get_logger().info(f"Daemon for {self.trigger:^20} is stopped.")

    @staticmethod
    def register_shutdown_handlers() -> None:
        """
        Handle shutdown signals.
        """
        # Register signal handlers for graceful shutdown
        # Handle termination signal
        signal.signal(signal.SIGTERM, handle_shutdown_signal)
        # Handle Ctrl+C
        signal.signal(signal.SIGINT, handle_shutdown_signal)
        get_logger().debug("Shutdown handlers registered.")
