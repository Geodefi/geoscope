from geode.utils.wrappers import httpRequest

from src.globals.sdk import SDK
from src.globals.config import CONFIG


# getting the block fetching mode from config.json. It is either 'latest' or 'finalized'
block_mode = CONFIG.chains[SDK.network.name].mode

# TODO: need to add these into the SDK and use from there


@httpRequest
def get_epoch(epoch: int or str = block_mode) -> str:
    """
    returns the corresponding epoch
    an epoch number can be specified, if not block_mode is applied
    """
    return SDK.Beacon.api_base + f"epoch/{epoch}" + SDK.Beacon.api_suffix


@httpRequest
def get_slots(epoch: int or str = block_mode) -> str:
    """
    returns the slots of the corresponding epoch
    an epoch number can be specified, if not block_mode is either 'latest' or 'finalized'
    """
    return SDK.Beacon.api_base + f"epoch/{epoch}/slots" + SDK.Beacon.api_suffix


def get_block_number() -> int:
    """
    Retrieves the latest or finalized block number
    """
    epoch: str = get_epoch()["epoch"]
    block_number: int = 0
    while block_number == 0:
        # incase all the slots in the epoch have missed a block! wtf...
        if epoch == 0:
            # incase all the beacon chain is a lie! wtf...
            raise Exception("All the beacon chain is a lie?!?!")
        slots: list = get_slots()

        # Find the maximum block number among the slots using the "exec_block_number" key
        block_number: int = max(slots, key=lambda i: i["exec_block_number"])[
            "exec_block_number"
        ]
        epoch -= 1
    return block_number
