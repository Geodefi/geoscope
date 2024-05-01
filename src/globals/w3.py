from web3 import Web3, HTTPProvider, WebsocketProvider
from web3.middleware import geth_poa_middleware
from globals.env import PRIVATE_KEY, EXECUTION_API

if PRIVATE_KEY:
    try:
        # If private key is provided but incorrect, raise error, quit
        if len(PRIVATE_KEY) == 64:
            PRIVATE_KEY = '0x' + PRIVATE_KEY
        elif len(PRIVATE_KEY) == 66 and PRIVATE_KEY[0:2] == '0x':
            pass
        else:
            raise
    except:
        raise Exception(
            "Invalid Private Key is Provided")
else:
    raise Exception(
        "No PRIVATE_KEY provided")

try:
    if EXECUTION_API[0:5] == 'https':
        provider = HTTPProvider(url)
    elif EXECUTION_API[0:3] == 'wss':
        provider = WebsocketProvider(url)

    W3 = Web3(provider)

    # Inject poa middleware
    W3.middleware_onion.inject(
        geth_poa_middleware, layer=0)

except:
    raise Exception("Invalid Network/RPC endpoint")