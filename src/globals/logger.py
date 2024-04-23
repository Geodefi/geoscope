from ..utils.log import initLogger
from ..globals import CONFIG, LOG_LEVEL

LOGGER = initLogger(dir=CONFIG["directories"]["logger"], log_level=LOG_LEVEL)
