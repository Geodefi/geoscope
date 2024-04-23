import numpy as np

from ..globals.sdk import SDK
from ..globals.config import CONFIG
from ..classes import Daemon, Trigger
from ..utils.multithread import multithread
from ..utils.list import find_missing
from ..utils.chain import get_block_number


class BlockDaemon(Daemon):
    """
    Watches an ethereum-like blockchain and processes its blocks by checking every [interval] seconds.
    """

    __state: dict = {
        "name": "block_daemon",
        "index": "blockNumber",
        "columns": {
            "hash": "str",
            "parentHash": "str",
            "fee_recipient": "str",
            "timestamp": "uint64",
            "withdrawals": "object",  # dict
        },
    }

    def __init__(self, interval: int, triggers: list[Trigger]) -> None:
        Daemon.__init__(
            self,
            structure=BlockDaemon.__state,
            interval=interval,
            task=self.listen_blocks,
            triggers=triggers,
        )

        self.register_verification(self.verify_blocks)

    def __update_block(self, number: int) -> dict:
        """
        Fecth and process one block, update the state and return the data.
        """
        block: dict = BlockDaemon.process_block(number)
        self.update(index=number, data=block)
        return block

    def __update_many_blocks(self, numbers: list[int]) -> dict:
        """
        Fecth and process many blocks, update the state and return the data.
        """
        blocks: list[dict] = multithread(BlockDaemon.process_block, numbers)
        self.update_many(dict(zip(numbers, blocks)), mode="merge")
        return blocks

    @staticmethod
    def process_block(number: int) -> dict:
        """
        Fetches the given block number and processes to make the data compatible with for BlockDaemon.__state.columns
        Note that, on goerli some blocks don't have 'withdrawals', but its ok will be inserted as [].
        """
        if number % 1000 == 0:  # todo_finally delete this.
            print(f"Updating: {number}", flush=True, end="\r")
        block = SDK.w3.eth.get_block(number)

        return {
            "hash": block.hash.hex(),
            "parentHash": block.parentHash.hex(),
            "fee_recipient": str(block.miner),
            "timestamp": int(block.timestamp),
            "withdrawals": [dict(x) for x in block.withdrawals],
        }

    def verify_blocks(self, mode: str):
        """
        DOES NOT VERIFY THE CORRECTNESS OF THE STATE.
        Verifies the state by making sure:
        1. there are no missing blocks.
        2. compare parent and block hashes, making sure there are no hard forks.

        If mode is:
          'fix' = instead of asserting, fixes the issues by fetching the needed blocks.
          'alert' = sends notifications to the user and continues.
          'quit' = sends notifications to the user and quits the program.
        """

        # fetch the first block from config.json
        first_block: int = CONFIG.chains[SDK.network.name].first_block

        while True:
            # convert the existing blocks into a list
            block_scope: list = self.state.index.values.tolist()

            # add the first block if its missing in the scope
            if first_block not in block_scope:
                block_scope.insert(0, first_block)

            if mode == "fix":
                # fetch the latest/finalized block
                current_block: int = get_block_number()

                # add the last block if its missing in the scope
                if current_block not in block_scope:
                    block_scope.append(current_block)

            # fetch the missing blocks
            missing_blocks: list = find_missing(block_scope)

            if missing_blocks:
                if mode == "fix":
                    self.__update_many_blocks(missing_blocks)
                elif mode == "alert":
                    # todo: send notification and continue
                    raise
                elif mode == "quit":
                    # todo: send notification and quit
                    raise
            else:
                break

        while True:
            # Check all the block hashes with parentHash of the row above
            x = np.argwhere(
                self.state["hash"].shift(1).iloc[1:]
                != self.state["parentHash"].iloc[1:]
            )

            if x:
                if mode == "fix":
                    for i in x:
                        block = int(self.state.index[i[0]])
                        # fix all related blocks, then re-check
                        self.__update_many_blocks([block - 1, block, block + 1])
                elif mode == "alert":
                    # todo: send notification and continue running
                    raise
                elif mode == "quit":
                    # todo: send notification and quit
                    raise
            else:
                break

        self.checkpoint()

    def listen_blocks(self) -> dict:
        """
        check for new blocks and update the state accordingly
        """
        latest_block: int = get_block_number()
        synced_block: int = self.state.index.max()

        if latest_block is synced_block:
            return {}

        elif latest_block is synced_block + 1:
            new_block: dict = self.__update_block(latest_block)
            return {latest_block: new_block}

        else:
            new_block_numbers: list[int] = list(range(synced_block, latest_block + 1))
            new_blocks: list[dict] = self.__update_many_blocks(new_block_numbers)
            return dict(zip(new_block_numbers, new_blocks))
