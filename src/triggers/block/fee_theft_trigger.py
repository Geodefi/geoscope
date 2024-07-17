# -*- coding: utf-8 -*-

from src.classes.trigger import Trigger
from src.logger import log


class FeeTheftTrigger(Trigger):
    """Every X hours checks for fee theft.
    Prison the thief if the fee theft is detected.

    Attributes:
        name (str): name of the trigger to be used when logging etc. (value: FEE_THEFT)
    """

    name: str = "FEE_THEFT"

    def __init__(self) -> None:
        """Initializes a FeeTheftTrigger object. The trigger will process the changes of the daemon after a loop.
        It is a callable object. It is used to process the changes of the daemon. It can only have 1 action.
        """

        Trigger.__init__(self, name=self.name, action=self.check_fee_theft)
        log.debug(f"{self.name} is initated.")

    def check_fee_theft(self, *args, **kwargs) -> None:
        """Checks for fee theft and prison the thief if the fee theft is detected.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        log.info(f"{self.name} is triggered.")

        # TODO: fee theft check implementation
