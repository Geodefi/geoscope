# -*- coding: utf-8 -*-

from web3.middleware import construct_sign_and_send_raw_middleware
from geodefi import Geode

from src.exceptions import MissingPrivateKeyError, SDKError


def __set_web3_account(sdk: Geode, private_key: str) -> Geode:
    """Sets the web3 account to the private key provided in the environment variables.

    Args:
        sdk: Initialized Geode SDK instance.

    Returns:
        Geode: Initialized Geode SDK instance.
    """
    # Create account on Geode's web3py instance
    signer = sdk.w3.eth.account.from_key(private_key)

    # Allow Geodefi to use your private key on transact
    sdk.w3.middleware_onion.add(construct_sign_and_send_raw_middleware(signer))

    # Set default account if one address is used generally
    sdk.w3.eth.default_account = signer.address

    return sdk


def init_sdk(exec_api: str, cons_api: str, priv_key: str = None) -> Geode:
    """Initializes the SDK with the provided APIs and private key.
     If private key is provided, sets the web3 account.

    Args:
        exec_api (str): Execution API URL.
        cons_api (str): Consensus API URL.
        priv_key (str, optional): Private key to be used. Default is None.

    Returns:
        Geode: Initialized Geode SDK instance.

    Raises:
        SDKException: If an error occurs while initializing the SDK.
    """
    try:
        sdk: Geode = Geode(exec_api=exec_api, cons_api=cons_api)
        if not priv_key:
            raise MissingPrivateKeyError(
                "Problem occured while connecting to SDK, private key is missing in .env file."
            )
        sdk = __set_web3_account(sdk, priv_key)
        return sdk

    except Exception as e:
        raise SDKError("Could not connect to sdk. Please check your configuration.") from e
