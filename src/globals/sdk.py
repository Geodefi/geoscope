from ..globals.env import EXECUTION_API, CONSENSUS_KEY, PRIVATE_KEY
from ..utils.sdk import initSdk
from geode import Geode

# global SDK
SDK: Geode = initSdk(
    exec_api=EXECUTION_API, cons_key=CONSENSUS_KEY, priv_key=PRIVATE_KEY
)
