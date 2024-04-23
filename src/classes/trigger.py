from typing import Callable


class Trigger:
    """
    Bound to a Daemon, a Trigger also processes the changes of the daemon after a loop.
    Triggers can utilize the Stateful.state as well, but mainly is not very state oriented.
    A trigger can only have 1 action, since we do not want the state to be mutated by multiple actions
    and cause a race condition and data ambigiuty
    """

    def __init__(self, structure: dict[str, type], action: Callable):
        self.__register_action(action)

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
            self.__action(changes)
        except Exception as e:
            raise e
