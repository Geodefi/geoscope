# -*- coding: utf-8 -*-

import sys
from web3.contract.contract import ContractEvent

from src.common import AttributeDict, Loggable
from src.daemons import BlockDaemon, EventDaemon
from src.triggers.event import VerificationTrigger, StakeProposalTrigger
from src.triggers.block import FeeTheftTrigger, MerkleTrigger
from src.globals import (
    set_config,
    set_env,
    set_sdk,
    set_constants,
    get_constants,
    set_logger,
    get_sdk,
    get_logger,
)
from src.globals.config import apply_flags, init_config
from src.globals.constants import init_constants
from src.globals.sdk import init_sdk
from src.utils.env import load_env

from src.common import Loggable

from src.database.validators import (
    reinitialize_validators_table,
    create_validators_table,
)
from src.database.events import (
    reinitialize_stake_proposal_table,
    create_stake_proposal_table,
)


def setup(**kwargs):
    """Initializes the required components from the gescope script:
    - Loads environment variables from specified .env file
    - Applies the provided flags to be utilized in the config step
    - Creates a config dict from provided json
    - Configures the geodefi python sdk
    - Configures the constant parameters for ease of use

    Args:
        flag_collector (Callable): a fuunction that provides the will
        provide the provided flags with the help of argparse lib.
        Secondary scripts can have their own flags, then this should be speciifed.
        Otherwise, defaults to collect_flags.
    """
    flags: AttributeDict = AttributeDict({k: v for k, v in kwargs.items() if v is not None})

    config = apply_flags(init_config(flags.main_dir), flags, env)
    set_config(config)

    # TODO: create init_constants() function
    # set_constants(init_constants())

    logger: Loggable = Loggable()
    set_logger(logger)

    set_sdk(
        init_sdk(
            exec_api=config.chains[config.chain_name].execution_api,
            cons_api=config.chains[config.chain_name].consensus_api,
            priv_key=env.PRIVATE_KEY,
        )
    )

    # TODO: implement preflight_checks() after correcting the apply_flags function
    # preflight_checks()


def init_dbs(reset: bool = False):
    """Initializes the databases as suited.\
    This function is called at the beginning of the program to make sure the
    databases are up to date.

    Args:
        reset (bool, optional): Wipes out all data if provided. Defaults to False.
    """
    if reset:
        get_logger().warning("Dropping the database...")

        reinitialize_stake_proposal_table()
        reinitialize_validators_table()

    else:
        create_validators_table()
        create_stake_proposal_table()


def run_daemons():
    """Initializes and runs the daemons for the triggers.

    This function is called at the beginning of the program to make sure the
    daemons are running.
    """
    events: ContractEvent = get_sdk().portal.contract.events

    # Triggers
    fee_theft_trigger: FeeTheftTrigger = FeeTheftTrigger()
    stake_proposal_trigger: StakeProposalTrigger = StakeProposalTrigger()
    verification_trigger: VerificationTrigger = VerificationTrigger()
    merkle_trigger: MerkleTrigger = MerkleTrigger()

    # Create appropriate type of Daemons for the triggers
    fee_theft_daemon: BlockDaemon = BlockDaemon(trigger=fee_theft_trigger, block_period=1)
    merkle_daemon: BlockDaemon = BlockDaemon(
        trigger=merkle_trigger,
        block_period=12 * get_constants().hour_blocks,
    )
    verification_daemon: EventDaemon = EventDaemon(
        trigger=verification_trigger,
        event=events.Verification(),
    )
    stake_proposal_daemon: EventDaemon = EventDaemon(
        trigger=stake_proposal_trigger,
        event=events.StakeProposal(),
    )

    # Run the daemons
    fee_theft_daemon.run()
    merkle_daemon.run()
    verification_daemon.run()
    stake_proposal_daemon.run()


# main.py
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

    fee_theft_daemon: BlockDaemon = BlockDaemon(trigger=fee_theft_trigger, block_period=1)

    merkle_daemon: BlockDaemon = BlockDaemon(
        trigger=merkle_trigger,
        block_period=12,  # TODO: Discuss this value
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
