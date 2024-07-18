# -*- coding: utf-8 -*-

from web3.middleware import construct_sign_and_send_raw_middleware
from geode import Geode

from src.exceptions.globals.sdk import SDKError


def initSdk(exec_api: str, cons_key: str, priv_key: str = None) -> Geode:
    """
    Initialize an SDK object according to the env vars and return
    """
    try:
        sdk: Geode = Geode(exec_api=exec_api, cons_key=cons_key)

        if priv_key:
            # Create account on Geode's web3py instance
            acct = sdk.w3.eth.account.from_key(priv_key)

            # Allow Geodefi to use your private key
            sdk.w3.middleware_onion.add(
                construct_sign_and_send_raw_middleware(acct)
            )

            # Set default account if one address is used generally
            sdk.w3.eth.defaultAccount = acct

        return sdk

    except Exception as e:
        raise SDKError() from e
