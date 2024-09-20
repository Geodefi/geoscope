# -*- coding: utf-8 -*-

from src.common.attribute_dict import AttributeDict
from src.globals import get_config


# TODO: ORACLE ADDRESS
def init_constants():
    config = get_config()
    return AttributeDict.convert_recursive(
        {
            "chain": config.chains[config.chain_name],
        }
    )
