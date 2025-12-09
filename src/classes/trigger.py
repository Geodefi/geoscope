"""
Trigger Management Module for Daemon Integration.

Provides the `Trigger` class, which is responsible for processing the changes of a Daemon
after each loop iteration. 

The Trigger binds a callable action to be executed during daemon processing.

Trigger ensures proper handling of actions, manages trigger names, and includes error handling for
invalid inputs.

Classes:
    Trigger: Manages an action to be executed by a Daemon.

Usage:
    def action():
        print("Action triggered")

    t = Trigger(action, name="MyTrigger")
    daemon = Daemon(interval=5, task=a_task, trigger=t)
    daemon.run()
    daemon.stop()
"""

from typing import Any, Callable

from src.globals import get_logger


class Trigger:
    """
    A trigger, bound to a Daemon, is responsible for processing daemon changes
    after each loop iteration. A Trigger is associated with a Daemon and is responsible
    for executing a single action whenever the Daemon processes changes.

    There can be only one action bound to each Trigger, promoting a clear and manageable workflow.

    Example:
        .. code-block:: python

            def action():
                print(datetime.datetime.now())

            trigger_instance = Trigger(action, name="TimePrinter")
            daemon = Daemon(interval=3, task=a_task, trigger=trigger_instance)
            daemon.run()
            # The daemon will execute `a_task` every 3 seconds, invoking `action` via the Trigger.
            daemon.stop()


    Attributes:
        __action (Callable): The function to be executed when the Trigger is invoked.
        name (str): The UNIQUE name for the Trigger, used for logging and identification purposes.
    """

    _registered_names: set = set()

    def __init__(self, action: Callable[..., Any], name: str = "UNKOWN_TRIGGER") -> None:
        """
        Initialize a Trigger instance with a specific action and name.

        The Trigger is designed to process changes from the associated Daemon
        by executing the provided action.

        Each Trigger must have a unique name between 5 and 17 characters to ensure
        proper identification and logging.

        Args:
            action (Callable): The function to be executed when the Trigger is invoked.
            name (str, optional): The name of the Trigger for identification and logging purposes.
                                Must be between 5 and 17 characters. Defaults to an empty string.
                                Default name is UNKOWN_TRIGGER.

        Raises:
            ValueError: If the provided name exceeds 17 characters or is shorter than 5 characters.
            TypeError: If the provided action is not a callable object.
        """

        self.__register_name(name)
        self.__register_action(action)
        get_logger().debug(f"Trigger {name} is initialized.")

    def __str__(self) -> str:
        """
        Return the name of the Trigger when the object is printed.

        Returns:
            str: The name of the Trigger.
        """
        return self.name

    def __format__(self, format_spec: str) -> str:
        """
        Custom format method for the Trigger class. Allows formatting with alignment,
        padding, etc.

        Args:
            format_spec (str): A string specifying the format (e.g., alignment or width).

        Returns:
            str: The formatted representation of the Trigger's name.
        """
        # If no format_spec is provided, return the name as is
        if not format_spec:
            return self.__str__()

        # Otherwise, format the name using the format_spec
        return format(self.name, format_spec)

    def __register_name(self, name: str) -> None:
        """
        Register a unique name of the Trigger and ensure it adheres to the length constraints.

        Validates the length of the provided name to ensure it is between the defined minimum
        and maximum limits. If valid, the name is stored as an attribute and registered in the
        class-wide set of names.

        Args:
            name (str): Unique Name of the Trigger instance. Must be between 5 and 17 characters.

        Raises:
            ValueError: If the length of the name is not within the specified range.
        """
        __name_min: int = 5
        __name_max: int = 17
        if not __name_min <= len(name) <= __name_max:
            raise ValueError(
                f"Name length should be between {__name_min} and {__name_max} characters."
            )
        self.name: str = name
        self._registered_names.add(name)

    def __register_action(self, action: Callable) -> None:
        """
        Register the action to be executed by the Trigger.

        Assigns the provided callable to the Trigger's internal action attribute.
        Only one action can be attached to a Trigger instance.

        Args:
            action (Callable): The function to be executed when the Trigger is invoked.

        Raises:
            TypeError: If the provided action is not a callable object.
        """

        if not callable(action):
            raise TypeError("The 'action' parameter must be callable.")

        self.__action: Callable = action

    def process(self, *args: Any, **kwargs: Any) -> None:
        """
        Execute the registered action with the provided arguments.

        This method is called by the Daemon to process changes. It logs the triggering event
        and executes the bound action, passing along any arguments or keyword arguments.

        Args:
            *args (Any): Variable length argument list to be passed to the action.
            **kwargs (Any): Arbitrary keyword arguments to be passed to the action.
        """

        get_logger().info(f"{self.name} is triggered.")
        self.__action(*args, **kwargs)

    def close(self) -> None:
        """
        Perform any necessary cleanup for the Trigger.
        """
        # Example: unregister from a registry
        self._registered_names.discard(self.name)
