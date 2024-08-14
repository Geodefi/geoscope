# -*- coding: utf-8 -*-

from geodefi.globals import VALIDATOR_STATE, DEPOSIT_SIZE, GENESIS_FORK_VERSION

from src.classes import Trigger

from src.globals import get_logger, get_sdk
from src.database.validators import (
    create_validators_table,
)
from src.database.events import create_stake_proposal_table
from src.helpers.portal import get_StakeParams
from src.actions.portal import call_updateVerificationIndex


class VerificationTrigger(Trigger):
    """Triggered regularly. Checks the validator proposals and approves them.

    Attributes:
        name (str): name of the trigger to be used when logging etc. (value: VERIFICATION)
    """

    name: str = "VERIFICATION"

    def __init__(self) -> None:
        """Initializes a VerificationTrigger object. The trigger will process the changes of the daemon after a loop.
        It is a callable object. It is used to process the changes of the daemon. It can only have 1 action.
        """

        Trigger.__init__(self, name=self.name, action=self.check_new_validators)
        create_validators_table()
        create_stake_proposal_table()
        get_logger().debug(f"{self.name} is initated.")
