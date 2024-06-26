# -*- coding: utf-8 -*-

from os import getenv
from dotenv import load_dotenv

load_dotenv()

# catch environment variables
EXECUTION_API = getenv("EXECUTION_API", None)
CONSENSUS_API = getenv("CONSENSUS_API", None)
PRIVATE_KEY = getenv("PRIVATE_KEY", None)
