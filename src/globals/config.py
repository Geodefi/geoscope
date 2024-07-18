# -*- coding: utf-8 -*-

import json

from src.common import AttributeDict

# catch configuration variables
config_dict: dict = json.load(open("config.json"))

# turn the config into AttributeDict recursively, so we can use dot notation
CONFIG: AttributeDict = AttributeDict.convert_recursive(config_dict)
