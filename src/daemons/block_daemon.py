# -*- coding: utf-8 -*-

from src.classes import Daemon, Trigger
from src.globals import SDK, chain

from src.logger import log


class BlockDaemon(Daemon):
    """A Daemon that triggers provided actions on every X block on the blockchain.
    Interval is default block time (12s).
    Task returns: last block number which activates the triggers.

    Example:
        def action():
            print(datetime.datetime.now())

        t = Trigger(action)
        b = BlockDaemon(trigger=t)

    Attributes:
        __recent_block (int): recent block number to be processed.
        block_period (int): number of blocks to wait before running the trigger.
        block_identifier (int): block_identifier sets if we are looking for 'latest', \
            'earliest', 'pending', 'safe', 'finalized'.
    """

    def __init__(
        self,
        trigger: Trigger,
        block_period: int = int(chain.period),
    ) -> None:
        """Initializes a BlockDaemon object. The daemon will run the triggers on every X block.

        Args:
            trigger (Trigger): an initialized Trigger instance.
            block_period (int, optional): number of blocks to wait before \
                running the triggers. Default is what is set in the config.
        """
        Daemon.__init__(
            self,
            interval=int(chain.interval),
            task=self.listen_blocks,
            trigger=trigger,
        )

        # block_identifier sets if we are looking for:
        # 'latest', 'earliest', 'pending', 'safe', 'finalized'.
        self.block_identifier: int = chain.identifier
        self.__recent_block: int = chain.start
        self.block_period: int = block_period
        log.debug(f"{trigger.name} is attached to a Block Daemon")

    def listen_blocks(self) -> int:
        """The main task for the BlockDaemon.
        1. Checks for new blocks.
        2. On every X block (period by config), runs the trigger. Returns the last block number.

        Returns:
            int: last block number which activates the trigger.
        """
        # eth.block_number or eth.get_block_number() can also be used
        # but this allows block_identifier.
        curr_block = SDK.w3.eth.get_block(self.block_identifier)
        log.debug(f"New block detected: {curr_block.number}")

        # check if required number of blocks have past:
        if curr_block.number >= self.__recent_block + self.block_period:
            #   returns the latest block number
            self.__recent_block = curr_block.number
            log.debug(f"{self.trigger.name} will be triggered")
            return curr_block
        else:
            log.debug(
                f"Block period have not been met yet.\
                Expected block:{self.__recent_block + self.block_period}"
            )
            return None
