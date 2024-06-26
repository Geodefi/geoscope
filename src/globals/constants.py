# -*- coding: utf-8 -*-

from .config import CONFIG
from .sdk import SDK

network: str = SDK.network.name
chain: dict = CONFIG.chains[network]
hour_blocks: int = 3600 // int(chain.interval)

# TODO: check block_seconds if can be fetched from chain

# assuming avg  1 block == 12 sec
block_seconds: int = 12

# number of blocks to divide the given range into multiple ranges while searching for events
EVENT_STEP: int = 1_000_000

# Minimum number of confirmations before processing a validator proposal
MIN_BLOCK_DELAY: int = 50

# Minimum blocks to wait for at least 5 validators to be proposed
MIN_VERIFICATION_DELAY: int = 1 * hour_blocks

# Maximum blocks to wait for any validator proposal
MAX_VERIFICATION_DELAY: int = 8 * hour_blocks

# Minimum number of validator proposals before considering approvals with MIN_VERIFICATION_DELAY
PENDING_PROPOSALS_THRESHOLD: int = 5

# Merkles are updated at most every 24h
MAX_MERKLE_DELAY: int = 24 * hour_blocks

# MAX_MERKLE_DELAY in seconds
MAX_MERKLE_DELAY_SECONDS: int = MAX_MERKLE_DELAY * block_seconds

# Maximum price change before merkle update is triggered, as a percentage.
# Note that currently this can not be a float value.
PRICE_CHANGE_THRESHOLD_PERCENTAGE: int = 1


NULL_ADDRESS = "0x0000000000000000000000000000000000000000"

WATCHER_URLS = [
    "https://watcher-api-fb725db20caa.herokuapp.com/v1/ethereum/reportOracle"
]

ATTEMPT = 10
