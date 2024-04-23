from typing import Callable
from threading import Thread, Event

from ..globals.exceptions import DeadDaemonException, DaemonStoppedException
from .stateful import Stateful, Status
from .trigger import Trigger


class Daemon(Stateful):
    """
    A daemon repeats a specific task with given interval as a period.
    Daemons use a single thread to run a loop at the background.
    However, a task can use multiprocessing to make things faster (not suggested)

    An example:
      ```
      def print_time():
        print(datetime.datetime.now())

      def quick_run():
        a= Daemon(interval=3, task=print_time)
        a.run()

        x=0
        while x<12:
          print("second")
          time.sleep(1)
          x+=1

        a.stop()
      ```
    """

    def __init__(
        self, interval: int, task: Callable, structure: dict, triggers: list[Trigger]
    ):
        Stateful.__init__(
            self,
            name=structure["name"],
            index=structure["index"],
            columns=structure["columns"],
        )

        self.__set_task(task)
        self.__set_interval(interval)
        self.__set_triggers(triggers)
        self.set_status(Status.INITIATED)

        self.startFlag: Event = Event()
        self.stopFlag: Event = Event()

    @property
    def interval(self) -> int:
        "waiting period in seconds"
        return self.__interval

    def __set_interval(self, interval: int):
        self.__interval: int = interval

    def __set_task(self, task: Callable):
        """
        __task should return a dict that will be used to update the state with update_many.
        """
        self.__task: Callable = task

    def __set_triggers(self, triggers: list[Trigger]):
        self.triggers: list[Trigger] = triggers

    def __initialize_triggers(self):
        if self.triggers:
            for f in self.triggers:
                f.verify(self.state, mode="fix")

    def __loop(self):
        while not self.stopFlag.wait(self.interval):
            try:
                # run the task and update the state
                self.set_status(Status.ACTIVE)
                changes: dict = self.__task()

                if len(changes) > 0:
                    # check for the triggers and run the actions => TODO_unrelated parallelize
                    if self.triggers:
                        [f.process(changes) for f in self.triggers]

                # finish the loop
                self.set_status(Status.WAITING)

            except:
                self.startFlag.clear()
                self.stopFlag.set()
                self.set_status(Status.STOPPED)
                raise DaemonStoppedException

    def run(self):
        if self.startFlag.is_set():
            raise  # todo change name
        self.stopFlag.clear()

        self.rollup()
        self.verify(mode="fix")
        self.__initialize_triggers()

        self.__worker = Thread(name="background", target=self.__loop)
        self.__worker.start()
        self.logger.info(
            f"{self.name}: running. Use stop() to stop, and CTRL+Z to exit."
        )
        self.startFlag.set()

    def stop(self):
        if not self.startFlag.is_set() or self.stopFlag.is_set():
            raise DeadDaemonException  # todo change name

        self.set_status(Status.STOPPED)
        self.stopFlag.set()
