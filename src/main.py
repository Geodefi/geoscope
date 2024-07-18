# -*- coding: utf-8 -*-

import sys
from web3.contract.contract import ContractEvent

from src.common import Loggable
from src.globals import set_logger, get_sdk
from src.daemons import BlockDaemon, EventDaemon
from src.triggers.block import FeeTheftTrigger

# TODO: update triggers with new ones
from src.triggers.block import MerkleTrigger
from src.triggers.event import VerificationTrigger
from src.globals.constants import hour_blocks

# TODO: check all SDK calls in the project


def setup_daemons():
    """Initializes and runs the daemons for the triggers.

    This function is called at the beginning of the program to make sure the
    daemons are running.
    """
    events: ContractEvent = get_sdk().portal.contract.events

    # Triggers
    fee_theft_trigger: FeeTheftTrigger = FeeTheftTrigger()
    merkle_trigger: MerkleTrigger = MerkleTrigger()
    verification_trigger: VerificationTrigger = VerificationTrigger()

    # Create appropriate type of Daemons for the triggers
    verification_daemon: EventDaemon = EventDaemon(
        trigger=verification_trigger, event=events.StakeProposal()
    )

    fee_theft_daemon: BlockDaemon = BlockDaemon(
        trigger=fee_theft_trigger, block_period=1
    )

    merkle_daemon: BlockDaemon = BlockDaemon(
        trigger=merkle_trigger,
        block_period=12 * hour_blocks,  # TODO: Discuss this value
    )

    # Run the daemons

    verification_daemon.run()
    fee_theft_daemon.run()
    merkle_daemon.run()


def main():
    """Main function of the program.

    This function is called when the program is run.

    initializes and sets up the daemons.
    """

    logger: Loggable = Loggable()
    set_logger(logger)

    try:
        setup_daemons()

    # pylint: disable-next=broad-exception-caught
    except Exception as e:
        sys.exit(e)


if __name__ == "__main__":
    main()
