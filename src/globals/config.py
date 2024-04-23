import json
from ..utils.attributeDict import AttributeDict, convert_recursive

# catch configuration variables
config_dict: dict = json.load(open("config.json"))

# turn the config into AttributeDict recursively, so we can use dot notation
CONFIG: AttributeDict = convert_recursive(config_dict)
