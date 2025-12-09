from geodefi import Geode
from web3.middleware.signing import construct_sign_and_send_raw_middleware

from src.exceptions import MissingPrivateKeyError, SDKError


def __set_web3_account(sdk: Geode, private_key: str) -> Geode:
    """
    Configure the Web3 account in the Geode SDK using the provided private key.

    Creates an account from the given private key, adds the signing middleware
    to the Web3 middleware stack, and sets the default account for transactions.

    Args:
        sdk (Geode): An initialized Geode SDK instance.
        private_key (str): The private key to set up the Web3 account.

    Returns:
        Geode: The updated Geode SDK instance with the Web3 account configured.

    Raises:
        ValueError: If the provided private key is invalid.
    """
    if not isinstance(private_key, str) or len(private_key) != 64:
        raise ValueError("Private key must be a 64-character hexadecimal string.")

    try:
        # Create account from private key
        signer = sdk.w3.eth.account.from_key(private_key)
    except ValueError as e:
        raise ValueError(f"Invalid private key provided: {e}") from e

    # Add signing middleware to SDK Web3 instance
    sdk.w3.middleware_onion.add(construct_sign_and_send_raw_middleware(signer))

    # Set signer as the default account
    sdk.w3.eth.default_account = signer.address

    return sdk


def init_sdk(exec_api: str, cons_api: str, priv_key: str | None) -> Geode:
    """
    Initialize the Geode SDK with specified execution and consensus APIs.
    Set the required Web3 account as default.

    Args:
        exec_api (str): Execution API URL.
        cons_api (str): Consensus API URL.
        priv_key (str, optional): Private key for setting up the Web3 account. Defaults to None.

    Returns:
        Geode: An initialized Geode SDK instance.

    Raises:
        MissingPrivateKeyError: If a private key is required but not provided.
        SDKError: If an error occurs during SDK initialization or account setup.
    """
    try:
        sdk: Geode = Geode(exec_api=exec_api, cons_api=cons_api)
        if not priv_key:
            raise MissingPrivateKeyError(
                "Private key is missing. Please provide a private key in .env file."
            )
        sdk = __set_web3_account(sdk, priv_key)
        return sdk

    except Exception as e:
        raise SDKError("Could not connect to sdk. Please check your configuration.") from e
