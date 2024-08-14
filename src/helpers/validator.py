# -*- coding: utf-8 -*-
from src.globals import get_sdk


def ping_pubkey_balance(pubkey: str, expected_balance: int) -> bool:
    """Checks if a validator pubkey can be reached on beaconchain.
    If it exists (not considering its status) it checks for the balance.
    Validators should be proposed in a proposeStake call previously.
    Unusually, it checks if the underlying call
    fires an error since it got 404 as a response instead of 200.

    Args:
        pubkey (str): public key of the validator to be pinged
        expected_balance (str): expected effective balance.

    Returns:
        bool: True if the validator exists on the beaconchain, False if not.
    """
    try:
        res = get_sdk().beacon.beacon_states_validators_id(state_id="head", validator_id=pubkey)
        return int(res["validator"]["balance"]) == expected_balance
    except Exception:
        return False


def ping_pubkey_status(pubkey: str, expected_status: str) -> bool:
    """Checks if a validator pubkey can be reached on beaconchain.
    If it exists, it checks if the status matches with the expected. 
    Note that, it is enough if the expected status is available as a substring.
    Validators should be proposed in a proposeStake call previously.
    Unusually, it checks if the underlying call
    fires an error since it got 404 as a response instead of 200.

    Args:
        pubkey (str): public key of the validator to be pinged
        expected_status (str): expected status of the validator.\
         pending (pending_initialized, pending_queued)\
            active
            

    Returns:
        bool: True if the validator exists on the beaconchain, False if not.
    """
    try:
        res = get_sdk().beacon.beacon_states_validators_id(state_id="head", validator_id=pubkey)
        return expected_status in str(res["status"])
    except Exception:
        return False
