# -*- coding: utf-8 -*-

from src.common.attribute_dict import AttributeDict
from src.globals import get_config, get_sdk
from src.helpers.portal import get_oracle_address
from src.actions.multisig import get_gnosis_safe


def init_constants() -> AttributeDict:
    """At this point, everything is set and tested.
    Here is the stuff that we don't want to calculate over and over again.

    Returns:
        AttributeDict: config as a dict object, that can also utilize dot notation
    """
    signer_address = get_sdk().w3.eth.default_account
    oracle_address = get_sdk().w3.to_checksum_address(get_oracle_address())
    oracle = get_gnosis_safe(oracle_address=oracle_address)
    config = get_config()
    chain: dict = config.chains[config.chain_name]
    # Log here if you can.

    return AttributeDict.convert_recursive(
        {
            "oracle_address": oracle_address,
            "oracle": oracle,
            "signer": signer_address,
            "chain": chain,
        }
    )


# TODO: I don't want to see get_constants(), all things related should be functionalized here.

# This folder should probably in utils or helpers.
# Same goes for sdk and config.
