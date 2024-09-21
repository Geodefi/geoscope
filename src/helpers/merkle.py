# -*- coding: utf-8 -*-

import os
from itertools import repeat
from multiproof import StandardMerkleTree
from web3.exceptions import ContractLogicError

from src.utils.thread import multithread
from src.globals import get_logger, get_sdk
from src.database.validators import fetch_pool_validators
from src.database.pools import fetch_timely_pool_data
from src.actions.multisig import send_tx
from src.helpers.validators import fetch_validator_balances
from src.helpers.portal import (
    fetch_batch_portal_state,
    get_oracle_update_timestamp,
    get_oracle_address,
)
from src.actions.multisig import get_gnosis


def calculate_fees_and_pending(
    pubkeys: list[str],
    validator_statuses: list[str],
    withdrawn_balances: list[str],
    pool_fees: list[str],
    operator_fees: list[str],
    infrastructure_fees: list[str],
    last_withdrawns: list[str],
    block_number: int,
) -> tuple:
    """Calculates the fees and pending rewards for a list of validators.

    Args:
        pubkeys (list[str]): The public keys of the validators.
        validator_statuses (list[str]): The statuses of the validators.
        withdrawn_balances (list[str]): The withdrawn balances of the validators.
        pool_fees (list[str]): The pool fees of the validators.
        operator_fees (list[str]): The operator fees of the validators.
        infrastructure_fees (list[str]): The infrastructure fees of the validators.
        last_withdrawns (list[str]): The last withdrawn balances of the validators.
        block_number (int): The block number to calculate the fees and pending rewards for.

    Returns:
        tuple: The fees and pending rewards as a tuple.
    """

    fees = 0
    pending = 0
    possible_pending_pks = []

    for i, validator_status in enumerate(validator_statuses):
        # since everything in lists are string we need to convert int when need
        withdrawn_balance = int(withdrawn_balances[i])
        pool_fee = int(pool_fees[i])
        operator_fee = int(operator_fees[i])
        infrastructure_fee = int(infrastructure_fees[i])
        last_withdrawn = int(last_withdrawns[i])

        if validator_status == "withdrawal_done":
            fees += (
                (withdrawn_balance - last_withdrawn)
                * (pool_fee + operator_fee + infrastructure_fee)
                / 1e10
            )
        else:
            fees += (withdrawn_balance * (pool_fee + operator_fee + infrastructure_fee)) / 1e10

        if validator_status == "pending_initialized":
            possible_pending_pks.append(pubkeys[i])

    portal_states = fetch_batch_portal_state(possible_pending_pks, block_number)

    # 32 eth in wei for each pending_initialized and portal state active (2) validator
    pending = portal_states.count(2) * 32 * 1e18

    return fees, pending


def calculate_pool_price(pool_id: int, block_number: int) -> dict:
    """Calculates the price of a pool and returns it as a dictionary.

    Args:
        pool_id (str): The pool id to calculate the price for.

    Returns:
        dict: The price of the pool as a dictionary.
    """
    str_pool_id = str(pool_id)

    # get all validators of the pool
    # fetch fee percentages (pool_fee, operator_fee, infrastructure_fee), withdrawn_balances, last_withdrawns and fee_recepient_balances from validators db
    # TODO: check if there is a chance for a validators any following values to be Null or None if so we need to handle it
    validator_data = fetch_pool_validators(str_pool_id)
    (
        pubkeys,
        pool_fees,
        operator_fees,
        infrastructure_fees,
        withdrawn_balances,
        last_withdrawns,
        fee_recepient_balances,
    ) = map(list, zip(*validator_data))

    # TODO: check if is guaranteed that these lists are in the same order with pubkeys
    #       otherwise we need to return the pubkeys from fetch_pool_validators and use it here to sort the lists
    validator_statuses, validator_balances = fetch_validator_balances(pubkeys)

    fulfilled_ether_balance, secured, surplus, total_supply, price = fetch_timely_pool_data(
        str_pool_id
    )

    fees, pending = calculate_fees_and_pending(
        pubkeys,
        validator_statuses,
        withdrawn_balances,
        pool_fees,
        operator_fees,
        infrastructure_fees,
        last_withdrawns,
        block_number,
    )

    validator_balance = (
        sum(validator_balances) + sum(withdrawn_balances) + sum(fee_recepient_balances)
    )

    total_balance = validator_balance - fulfilled_ether_balance - fees + pending + secured + surplus

    new_price = total_balance / total_supply

    return (
        pool_id,
        new_price,
        new_price / price > 1.01,  # if the price increased more than 1% return True else False
        pubkeys,
        validator_balances,
        withdrawn_balances,
    )


def calculate_prices(pool_ids: list[int], block_number: int) -> list[tuple]:
    """Calculates the prices of pools and returns them as a dictionary.

    Args:
        block_number (int): The block number to calculate the prices for.

    Returns:
        dict: The prices of the pools as a dictionary.
    """
    return multithread(calculate_pool_price, pool_ids, repeat(block_number))


def should_update_merkle(pool_ids: list[int], block_number: int) -> tuple[bool, list[tuple]]:
    """
    Checks the last update on merkle, if a configured! x(24h) amount has surpassed, update.
    Compares every pool for an increase of a configured! y(1) % change.
    Returns false otherwise.
    """

    should_update = False

    last_update_ts: int = get_oracle_update_timestamp(block_number)

    current_ts: int = get_sdk().w3.eth.get_block(block_number).timestamp

    # if 24 hours has passed since the last update, should update the merkle tree
    if current_ts - last_update_ts > 86400:  # 24 hours in seconds
        should_update = True
    else:
        return (False, None)

    data: list[tuple] = calculate_prices(pool_ids, block_number)

    if not should_update:
        should_update = any(obj[2] for obj in data)

    if should_update:
        return (True, data)
    return (False, None)


def build_balances_and_prices(data: list[tuple]) -> tuple[list, list]:
    """Builds the balances and prices for the validators.

    Args:
        data (list[tuple]): The data to build the balances and prices for.
                            [(pool_id, new_price, price_eligibility, pubkeys, validator_balances, withdrawn_balances), ...]

    Returns:
        tuple(list, list): The balances and prices for the validators.
    """

    prices = [[pool_id, new_price] for pool_id, new_price, *_ in data]
    balances = [
        [pubkey, validator_balance, withdrawn_balance]
        for *_, pubkeys, validator_balances, withdrawn_balances in data
        for pubkey, validator_balance, withdrawn_balance in zip(
            pubkeys, validator_balances, withdrawn_balances
        )
    ]

    return prices, balances


def prepare_report(balances: list, prices: list) -> tuple[str, str, int]:
    """Prepares the report for the balances and prices.

    Args:
        balances (list): The balances to prepare the report for.
        prices (list): The prices to prepare the report for.

    Returns:
        tuple: The report for the balances and prices.
    """

    # ----- pool price related calculations -----
    # create merkle tree for pool prices
    # prices --> [[pool_id, price]...]
    price_merkle_tree = StandardMerkleTree.of(prices, ["uint256", "uint256"])
    price_merkle_root = price_merkle_tree.root

    # ----- validator balances related calculations -----
    # create merkle tree for validator balances
    # balances --> [[pubkey, balance, withdrawn_balance]...]
    balance_merkle_tree = StandardMerkleTree.of(balances, ["bytes", "uint256", "uint256"])
    balance_merkle_root = balance_merkle_tree.root

    # ----- all validators on chain related calculations -----

    # NOTE: !!! for now we will send a fixed number, lets say 1m or someting like that.
    all_val_count = 1_000_000_000  # we can fetch if from oklink, but need to discuss this
    if all_val_count < 50_000:
        all_val_count = 50_000  # minimum count for the merkle tree

    return (balance_merkle_root, price_merkle_root, all_val_count)


# TODO: this function may be combined with multisig get_caller_data function or that one can be used here
def is_oracle_owner(block_number: int) -> bool:
    """Checks if the oracle is the owner.

    Returns:
        bool: True if the oracle is the owner, False otherwise.
    """

    private_key = os.getenv("GEOSCOPE_PRIVATE_KEY")
    if private_key is None:
        raise Exception("GEOSCOPE_PRIVATE_KEY is not set.")

    try:
        address = get_sdk().w3.eth.account.from_key(private_key).address
    except Exception as e:
        raise Exception("Invalid GEOSCOPE_PRIVATE_KEY") from e

    if not get_sdk().w3.is_checksum_address(address):
        address = get_sdk().w3.to_checksum_address(address)

    oracle_address = get_oracle_address(block_number)

    if not get_sdk().w3.is_checksum_address(oracle_address):
        oracle_address = get_sdk().w3.to_checksum_address(oracle_address)

    return address == oracle_address


def report_beacon(
    price_merkle_root: str, balance_merkle_root: str, all_validators_count: int, block_number: int
) -> None:
    """Reports the beacon.

    Args:
        price_merkle_root (str): The price merkle root.
        balance_merkle_root (str): The balance merkle root.
        all_validators_count (int): The all validators count.
        block_number (int): The block number to report the beacon for.
    """

    ## oracle is the owner's address -> if no multisig -> call portal
    ## oracle is not provided address -> if one address on multisig -> call multisig
    ##                                -> multiple addresses on multisig -> call watcher

    try:
        gnosis_contract = get_gnosis()
        owners = gnosis_contract.functions.getOwners().call()
    except:
        owners = None

    if is_oracle_owner(block_number) and owners is None:
        # call portal
        try:
            success, tx_receipt = send_tx(
                contract_address="0xcA69bA533810ee94b7649c57eF8aB22EBbE0bbf7",  # Portal contract address
                method_id="0xdf1ff929",  # reportBeacon function signature
                param_types=["bytes32", "bytes32", "uint256"],
                param_args=[price_merkle_root, balance_merkle_root, all_validators_count],
            )

            if success:
                get_logger().info(
                    f"Successfully sent transaction: {dict(tx_receipt)['transactionHash'].hex()}"
                )
            else:
                # TODO: decide how to handle error
                get_logger().error(
                    f"Failed to send transaction (reverted): {dict(tx_receipt)['transactionHash'].hex()}"
                )
        except ContractLogicError as e:
            # TODO: decide how to handle exception
            get_logger().error(f"Contract logic error: {str(e)}")
        except Exception as e:
            # TODO: decide how to handle exception
            get_logger().error(f"Error sending transaction: {str(e)}")
    elif owners is None:
        raise Exception("Cannot find the Gnosis Safe contract.")
    elif len(owners) == 1:
        # TODO: call multisig
        pass
    elif len(owners) > 1:
        # TODO: call watcher
        pass
    else:
        raise Exception("Some error occurred. Please contact the Geodefi Team.")

    # TODO: send post request to backend to update the chain
    # if state is active and balance less than 16, it is a problem, raise error and exit

    # ----- update backend -----
