"""
Helper functions for processing fee recipients and detecting potential thefts within given slots.
"""

from collections import defaultdict

from web3.types import BlockData, TxReceipt

from src.common import BigInteger
from src.database.slots import filter_slots_by_proposer
from src.database.validators import (
    increase_fee_recipient_balances,
    read_operator_id_by_beacon_index,
)
from src.globals import get_logger, get_sdk
from src.utils.thread import multithread


def detect_theft(slot_info: tuple) -> tuple[BigInteger, BigInteger] | None:
    """
    Detects unauthorized fee recipients in a given slot.

    Args:
        slot_info (tuple): A tuple containing slot details:
            - proposer_index (int): Beacon chain index for the proposer validator.
            - block_number (int): Block number, to be given as a proof
            - fee_recipient (str): Address of the fee recipient,
                expected to be same address with the withdrawal contract address.
            - burned_amount (int):  (not used) Cumulative amount burned in all txs.
            - withdrawal_contract_address (str): Expected withdrawal contract address.

    Returns:
        tuple[BigInteger, BigInteger] | None: Returns a tuple of (operator_id, block_number)
         if theft is detected, otherwise returns None.
    """
    proposer_index, block_number, fee_recipient, _, withdrawal_contract_address = slot_info

    if fee_recipient == withdrawal_contract_address:
        return None

    operator_id: BigInteger = read_operator_id_by_beacon_index(proposer_index)

    get_logger().debug(f"Detected theft on block: {block_number} . Thief: {operator_id}")

    return operator_id, block_number


def get_tx_fee(tx: dict) -> int:
    """
    Calculates the transaction fee for a single transaction.

    Args:
        tx (dict): A dictionary representing the transaction, required for the "hash" key,
            representing the Transaction Hash.

    Returns:
        int: The calculated transaction fee in Wei.
    """
    tx_receipt: TxReceipt = get_sdk().portal.w3.eth.get_transaction_receipt(tx["hash"])
    return int(tx_receipt["gasUsed"]) * int(tx_receipt["effectiveGasPrice"])


def compute_recipient_fee(slot_info: tuple) -> tuple[int, int]:
    """
    Computes the *total* fees received by the fee recipient for the given slot.

    Args:
        slot_info (tuple): A tuple containing slot details:
            - SLOTS_BLOCK_NUMBER_FIELD (int): Index of the proposer.
            - SLOTS_PROPOSER_INDEX_FIELD (int): Block number.
            - SLOTS_FEE_RECIPIENT_FIELD (str): Address of the fee recipient.
            - SLOTS_BURNED_AMOUNT_FIELD (BigInteger): Amount burned.
            - POOLS_WITHDRAWAL_CONTRACT_ADDRESS_FIELD (str): Withdrawal contract address.

    Returns:
        tuple: proposer_index, recipient profit
    """
    proposer_index, block_number, fee_recipient, burned_amount, withdrawal_contract_address = (
        slot_info
    )

    if fee_recipient != withdrawal_contract_address:
        # TODO:(later) the whole detect_theft function can be done here.
        # It makes things a lot faster, but no urgency.
        # TODO:(later)  MEV here.
        return proposer_index, 0

    block: BlockData = get_sdk().portal.w3.eth.get_block(block_number, full_transactions=True)

    tx_fees_sum: int = sum(multithread(get_tx_fee, block.get("transactions", {})))
    profit: int = tx_fees_sum - int(burned_amount)

    get_logger().debug(f"Accumulated tx fee on {block_number} is : {profit}")

    return proposer_index, profit


def process_fee_recipients(min_slot: int) -> list[tuple[BigInteger, BigInteger] | None]:
    """
    Processes fee recipients for a specific slot number:
    * Filtering relevant slots
      * have not been processed before.
      * proposed by the known validators.
    * Calculating and aggregating fees
    * Updating fee recipient balances
    * Detecting thefts and handling them.

    Args:
        min_slot (int): The slot number to start processing the block fees.
            Fees are processed until reaching the last slot in db.
    Returns:
        list[tuple[BigInteger, BigInteger] | None]: Returns a tuple of (operator_id, block_number)
         if theft is detected, otherwise returns None.
    """
    # Note that when we are sending the merkle roots, we include it in withdrawn_balance
    # Filter slots that has a proposer indice with the one
    proposed_slots: list[tuple[int, int, str, BigInteger, str]] = filter_slots_by_proposer(min_slot)
    if proposed_slots:
        get_logger().info(
            f"Detected {len(proposed_slots)} proposed slots. Processing block fees... "
        )
        indexed_fees: list[tuple[int, int]] = multithread(compute_recipient_fee, proposed_slots)

        total_profits_by_proposer: dict = defaultdict(int)
        for proposer_index, profit in indexed_fees:
            total_profits_by_proposer[proposer_index] += profit

        increase_fee_recipient_balances(total_profits_by_proposer)

        thefts: list[tuple[BigInteger, BigInteger] | None] = multithread(
            detect_theft, proposed_slots
        )
        # TODO:(later) In case the slots are processed/saved BUT exited before processing fees:
        # Set some parameter on the database, like last_fee_process, etc?

        if thefts:
            return thefts

    return []
