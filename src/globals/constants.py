# -*- coding: utf-8 -*-

#  TODO: delete this command block
# # number of blocks to divide the given range into multiple ranges while searching for events
# EVENT_STEP: int = 1_000_000

# # Minimum number of confirmations before processing a validator proposal
# MIN_BLOCK_DELAY: int = 50

# # Minimum time to wait for at least 5 validators to be proposed
# MIN_VERIFICATION_DELAY: int = 1 * hour_blocks * 12

# # Maximum time to wait for any validator proposal
# MAX_VERIFICATION_DELAY: int = 8 * hour_blocks * 12

# # Minimum number of validator proposals before considering approvals with MIN_VERIFICATION_DELAY
# PENDING_PROPOSALS_THRESHOLD: int = 5

# # Merkles are updated at most every 24h
# MAX_MERKLE_DELAY: int = 24 * hour_blocks

# # MAX_MERKLE_DELAY in seconds
# MAX_MERKLE_DELAY_SECONDS: int = MAX_MERKLE_DELAY * block_seconds

# # Maximum price change before merkle update is triggered, as a percentage.
# # Note that currently this can not be a float value.
# PRICE_CHANGE_THRESHOLD_PERCENTAGE: int = 1


# WATCHER_URLS = [
#     "https://watcher-api-fb725db20caa.herokuapp.com/v1/ethereum/reportOracle"
# ]

# ATTEMPT = 10 -> config

# -*- coding: utf-8 -*-

from src.common.attribute_dict import AttributeDict
from src.globals import get_config


def init_constants():
    config = get_config()
    return AttributeDict.convert_recursive(
        {
            "chain": config.chains[config.chain_name],
            "hour_blocks": 3600 // int(config.chains[config.chain_name].interval),
            "one_minute": 60,
            "one_hour": 3600,
        }
    )
