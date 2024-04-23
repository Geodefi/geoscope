from typing import Callable
from .stateful import Stateful, Status


class Trigger(Stateful):
    """
    Bound to a Daemon, a Trigger also processes the changes of the daemon after a loop.
    Triggers can utilize the Stateful.state as well, but mainly is not very state oriented.
    A trigger can only have 1 action, since we do not want the state to be mutated by multiple actions
    and cause a race condition and data ambigiuty
    """

    def __init__(self, structure: dict[str, type], action: Callable):
        Stateful.__init__(
            self,
            name=structure["name"],
            index=structure["index"],
            columns=structure["columns"],
        )

        self.__register_action(action)
        self.set_status(Status.INITIATED)

    def __register_action(self, action: Callable):
        """
        Sets an action to be called during processing of the daemon's changes
        """
        self.__action: Callable = action

    def process(self, changes: dict):
        """
        Process the action, __action might mutate .state
        """
        try:
            self.set_status(Status.ACTIVE)
            self.__action(changes)
            self.set_status(Status.WAITING)
        except:
            raise
