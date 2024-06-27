# -*- coding: utf-8 -*-

from typing_extensions import Self
from src.classes import Daemon, Trigger
from src.logger import log


class TimeDaemon(Daemon):
    """A Daemon that triggers provided actions on every X seconds. Task returns True, simply run.

    Example:
        def action():
            print(datetime.datetime.now())

        t = Trigger(action)
        b = TimeDaemon(trigger=t)
    """

    def __init__(self, interval: int, trigger: Trigger, initial_delay: int) -> None:
        Daemon.__init__(
            self,
            interval=interval,
            task=self.reflect,
            trigger=trigger,
            initial_delay=initial_delay,
        )

    def reflect(self) -> Self:
        """Returns self. Self will be used to stop the daemon when needed by trigger itself
        since return value will be passed to the trigger function.

        Returns:
            Self: self
        """
        log.debug(f"Time Daemon will be triggered.")
        return self
