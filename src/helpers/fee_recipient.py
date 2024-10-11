# -*- coding: utf-8 -*-

from collections import defaultdict

from src.database.slots import filter_by_proposer
from src.database.validators import (
    fetch_operator_id_by_beacon_index,
    increase_fee_recipient_balances,
)
from src.utils.thread import multithread
from src.globals import get_sdk


def filter_theft(slot_info: tuple) -> tuple:
    proposer_index, block_number, fee_recipient, _, withdrawal_contract_address = slot_info

    if fee_recipient == withdrawal_contract_address:
        return None

    return fetch_operator_id_by_beacon_index(proposer_index), block_number


def calculate_recipient_fee(slot_info: tuple) -> tuple:
    proposer_index, block_number, fee_recipient, burned_amount, withdrawal_contract_address = (
        slot_info
    )

    if fee_recipient != withdrawal_contract_address:
        # TODO: MEV here.
        return proposer_index, 0

    w3_eth = get_sdk().portal.w3.eth
    block = w3_eth.get_block(block_number, full_transactions=True)

    tx_fee_sum = 0
    for tx in block.transactions:
        tx_receipt = w3_eth.get_transaction_receipt(tx.hash)
        tx_fee = int(tx_receipt["gasUsed"]) * int(tx_receipt["effectiveGasPrice"])
        tx_fee_sum += tx_fee

    profit = tx_fee_sum - int(burned_amount)

    return proposer_index, profit


def process_fee_recipients(slot_num: int):
    # Note that when we are sending the merkle roots, we include it in withdrawn_balance
    # Filter slots that has a proposer indice with the one
    resulting_slots: list[tuple] = filter_by_proposer(slot_num)
    indexed_fees: list[tuple] = multithread(calculate_recipient_fee, resulting_slots)

    total_profits_by_proposer: dict = defaultdict(int)
    for proposer_index, profit in indexed_fees:
        total_profits_by_proposer[proposer_index] += profit

    increase_fee_recipient_balances(total_profits_by_proposer)

    thefts: list[tuple] = multithread(filter_theft, resulting_slots)
    thefts = list(filter(None, thefts))  # This will remove any None results

    if thefts:
        # TODO: call regulateOperators here.
