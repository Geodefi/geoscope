# -*- coding: utf-8 -*-

from multiproof import StandardMerkleTree
from web3.exceptions import ContractLogicError

from src.globals import get_logger
from src.database.validators import fetch_validator_balances
from src.actions.multisig import send_tx


def should_update_merkle(block_identifier: str) -> tuple[bool, dict]:
    """
    Checks the last update on merkle, if a configured! x(24h) amount has surpassed, update.
    Compares every pool for an increase of a configured! y(1) % change.
    Returns false otherwise.
    """
    return [False, None]


def build_balances_data() -> dict:
    """_summary_

    Returns:
        dict: _description_
    """


def prepare_report(prices: dict, balances: dict) -> tuple[
    int,
    int,
]:
    """_summary_"""
    # TODO: calculate prices and check how much it changed (it its more then 1% any price, can check from chain)
    # or if last updatetimestamp from stakeparams is more then 24 hours it will be updated for sure

    # ----- pool price related calculations -----
    pool_prices: dict = {}  # {pool_id: price}

    ids = pool_prices.keys()
    prices = pool_prices.values()
    price_merkle_tree = StandardMerkleTree.of([ids, prices], ["uint256", "uint256"])
    price_merkle_root = price_merkle_tree.root

    # ----- validator balances related calculations -----

    # validator_balances = [(pubkey, beacon_balance, withdrawn_balance), ...]
    validator_balances = fetch_validator_balances()

    # convert to lists
    pubkeys, beacon_balances, withdrawn_balances = map(list, zip(*validator_balances))

    # create merkle tree for validator balances
    balance_merkle_tree = StandardMerkleTree.of(
        [pubkeys, beacon_balances, withdrawn_balances], ["bytes", "uint256", "uint256"]
    )

    balance_merkle_root = balance_merkle_tree.root

    # ----- all validators on chain related calculations -----

    # TODO: get the count of all validators on chain
    # ! for now we will send a fixed number, lets say 1m or someting like that.
    all_val_count = 50_000  # we can fetch if from oklink, but need to discuss this
    if all_val_count < 50_000:
        all_val_count = 50_000  # minimum count for the merkle tree

    # ----- send tx to multisig to update chain -----
    # ! This should be in actions/portal: check update_merkle

    try:
        success, tx_receipt = send_tx(
            contract_address="0xcA69bA533810ee94b7649c57eF8aB22EBbE0bbf7",  # Portal contract address
            method_id="0xdf1ff929",  # reportBeacon function signature
            param_types=["bytes32", "bytes32", "uint256"],
            param_args=[price_merkle_root, balance_merkle_root, all_val_count],
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

    # TODO: send post request to backend to update the chain
    # if state is active and balance less than 16, it is a problem, raise error and exit

    # ----- update backend -----
    return None, None, None


def report_beacon(price_merkle_root: str, balance_merkle_root: str, all_validators_count: int):
    """_summary_"""
    ## oracle is the owner's address -> if no multisig -> call portal
    ## oracle is not provided address -> if one address on multisig -> call multisig
    ##                                -> multiple addresses on multisig -> call watcher

    # reportBeacon(
    #     bytes32 priceMerkleRoot,
    #     bytes32 balanceMerkleRoot,
    #     uint256 allValidatorsCount
    # )
