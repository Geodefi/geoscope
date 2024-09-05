# -*- coding: utf-8 -*-

import os
import signal
from time import sleep
from typing import Callable
from threading import Thread, Event
from web3.exceptions import TimeExhausted

from src.classes.trigger import Trigger
from src.exceptions import (
    DaemonError,
    CallFailedError,
    EmailError,
    HighGasError,
    EventFetchingError,
)
from src.globals import get_logger
from src.utils.notify import send_email


class Daemon:
    """A daemon repeats a specific task with given interval as a period.
    Daemons use a single thread to run a loop at the background to run all the provided trigger,
    and check for tasks on every iteration.

    .. code-block:: python
        def print_time():
            print(datetime.datetime.now())

        def quick_run():
            a = Daemon(interval=3, task=print_time)
            a.run()

        quick_run()

        a.stop()

    Attributes:
        __interval (int): Time duration between 2 tasks.
        __initial_delay (int): Initial delay before starting the loop.
        __task (Callable): Work to be done after every iteration.
        __worker (Thread): Thread object to run the loop.
        trigger (Trigger): an initialized Trigger instance.
        start_flag (Event): Event flag to start the daemon.
        stop_flag (Event): Event flag to stop the daemon.

    Raises:
        DaemonError: Raised in several cases, such as when the daemon is already running or stopped.
    """

    def __init__(
        self,
        interval: int,
        task: Callable,
        trigger: Trigger,
        initial_delay: int = 0,
    ) -> None:
        """Initializes a Daemon object. The daemon will run the task with the given interval.

        Args:
            interval (int): Time duration between 2 tasks.
            task (Callable): Work to be done after every iteration
            trigger (Trigger): an initialized Trigger instance
            initial_delay (int, optional): Initial delay before starting the loop. Defaults to 0.
        """
        get_logger().debug(
            f"Initializing a Daemon object. interval: {interval},"
            f"trigger:{trigger.name}, delay:{initial_delay}"
        )
        self.__set_task(task)
        self.__set_interval(interval)
        self.__set_initial_delay(initial_delay)
        self.__set_trigger(trigger)

        self.__worker: Thread = Thread(name=trigger.name, target=self.__loop)
        self.start_flag: Event = Event()
        self.stop_flag: Event = Event()
        get_logger().debug(f"Initialized a Daemon for: {trigger.name:^20}.")

    @property
    def interval(self) -> int:
        """Returns waiting period (in seconds), as a property

        Returns:
            int: Waiting period in seconds
        """

        return self.__interval

    @property
    def initial_delay(self) -> int:
        """Returns initial delay before starting the loop, as a property

        Returns:
            int: Initial delay in seconds
        """

        return self.__initial_delay

    def __set_interval(self, interval: int) -> None:
        """Sets waiting period to given interval on initialization.

        Args:
            interval (int): New waiting period
        """

        self.__interval: int = interval

    def __set_initial_delay(self, initial_delay: int) -> None:
        """Sets initial delay before starting the loop, on initialization.

        Args:
            initial_delay (int): New initial delay
        """

        self.__initial_delay: int = initial_delay

    def __set_task(self, task: Callable) -> None:
        """Sets the task for the daemon on initialization.
        Tasks should return a dict of effects to be checked by trigger.

        Args:
            task (function): New task to be done after every period.
        """

        self.__task: Callable = task

    def __set_trigger(self, trigger: Trigger) -> None:
        """Sets list of trigger that will be checked on every iteration, called on initialization.

        Args:
            trigger [Trigger] : an initialized Trigger instance
        """
        if isinstance(trigger, Trigger):
            self.trigger: Trigger = trigger
        else:
            raise TypeError("Given trigger is not an instince of Trigger")

    def __loop(self) -> None:
        """Runs the loop, checks for the task and trigger on every iteration.
        Stops when stop_flag is set.
        If the task raises an exception, the daemon stops and raises a DaemonError.
        This is to prevent the daemon from running with a broken task.
        The exception is raised to the caller to handle the error.
        The daemon can be restarted after the error is handled.
        The stop_flag is set to prevent the daemon from running again.

        Raises:
            DaemonError: Raised if the daemon stops due to an exception.
        """
        sleep(self.__initial_delay)

        while not self.stop_flag.wait(self.interval):
            try:
                result = self.__task()

                if result:
                    self.trigger.process(result)

                else:
                    pass

            except (TimeExhausted, CallFailedError):
                get_logger().warning(
                    f"One of the calls failed for {self.trigger.name:^20}."
                    " Continuing but may need to be checked in case of a problem."
                )
                try:
                    send_email(
                        "Tx failed",
                        " A Portal transaction is either failed,"
                        " or could not be called for some reason."
                        " Will continue operations as usual, but an investigation is suggested.",
                    )
                except EmailError:
                    get_logger().warning(
                        "Not able to communicate with the owners."
                        " Continuing without an assistance."
                    )
            except HighGasError as e:
                get_logger().error(str(e))
                get_logger().warning(
                    f"One of the calls failed for {self.trigger.name:^20}."
                    " Continuing but may need to be checked in case of a problem."
                )
                try:
                    send_email(
                        "High Gas Alert",
                        "On Chain gas api reported that gas prices have surpassed the max setting.",
                        dont_notify_devs=True,
                    )
                except EmailError:
                    get_logger().warning(
                        "Not able to communicate with the owners."
                        " Continuing without an assistance."
                    )
            except EventFetchingError as e:
                get_logger().error(str(e))
                try:
                    send_email(
                        "Could not get some events from the chain",
                        " There was an issue while fetching an event from the chain."
                        " Will not shot down geoscope and will be trying again later."
                        " However, it might be worth checking what is wrong.",
                        dont_notify_devs=True,
                    )
                except EmailError:
                    get_logger().warning(
                        "Not able to communicate with the owners."
                        " Continuing without an assistance."
                    )

                self.start_flag.clear()
                self.stop_flag.set()

            except Exception:
                # All of the remaining Exceptions will force the MainThread to exit.>
                get_logger().exception(
                    f"Stopping geoscope due to unhandled exception on a Daemon for:"
                    f"{self.trigger.name:^20}"
                )
                try:
                    send_email(
                        "STOPPED",
                        f"All Daemons stopped, script exited. Come take a look!",
                    )
                except EmailError:
                    get_logger().warning(f"Could not send email while exiting geoscope. Well...")

                os.kill(os.getpid(), signal.SIGUSR1)

    def run(self) -> None:
        """Starts the daemon, runs the loop when called.

        Raises:
            DaemonError: Raised if the daemon is already running.
        """
        if self.start_flag.is_set():
            get_logger().error("Stopping Geoscope")
            raise DaemonError("Daemon is already running.")
        self.stop_flag.clear()

        self.__worker.start()

        self.start_flag.set()
        get_logger().info(
            f"Daemon for {self.trigger.name:^20} will run every {self.interval} seconds."
        )

    def stop(self) -> None:
        """Stops the daemon, exits the loop.

        Raises:
            DaemonError: Raised if the daemon is already stopped.
        """

        # if already stopped
        if not self.start_flag.is_set() or self.stop_flag.is_set():
            get_logger().error("Stopping Geoscope")
            raise DaemonError("Daemon is already stopped.")

        self.stop_flag.set()
        get_logger().info(f"Daemon for {self.trigger.name:^20} is stopped.")
