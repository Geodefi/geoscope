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
