from os import getenv

# catch environment variables
READ_ONLY = getenv("READ_ONLY", True)
EXECUTION_API = getenv("EXECUTION_API", None)
CONSENSUS_KEY = getenv("CONSENSUS_KEY", None)
PRIVATE_KEY = getenv("PRIVATE_KEY", None)
PROVIDER_URL = getenv("PROVIDER_URL", None) # TODO: add provider_url to env