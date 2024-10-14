# -*- coding: utf-8 -*-

from collections import defaultdict

from src.database.slots import filter_slots_by_proposer
from src.database.validators import (
    read_operator_id_by_beacon_index,
    increase_fee_recipient_balances,
)
from src.utils.thread import multithread
from src.globals import get_sdk
from src.helpers.portal import handle_regulate_operators


def detect_theft(slot_info: tuple) -> tuple:
    proposer_index, block_number, fee_recipient, _, withdrawal_contract_address = slot_info

    if fee_recipient == withdrawal_contract_address:
        return None

    return read_operator_id_by_beacon_index(proposer_index), block_number


def get_tx_fee(tx: dict):
    tx_receipt: dict = get_sdk().portal.w3.eth.get_transaction_receipt(tx["hash"])
    return int(tx_receipt["gasUsed"]) * int(tx_receipt["effectiveGasPrice"])


def compute_recipient_fee(slot_info: tuple) -> tuple:
    proposer_index, block_number, fee_recipient, burned_amount, withdrawal_contract_address = (
        slot_info
    )

    if fee_recipient != withdrawal_contract_address:
        # TODO: (later)  MEV here.
        return proposer_index, 0

    block: dict = get_sdk().portal.w3.eth.get_block(block_number, full_transactions=True)

    tx_fees_sum: int = sum(multithread(get_tx_fee, block.transactions))

    return proposer_index, tx_fees_sum - int(burned_amount)


def process_fee_recipients(slot_num: int):
    # Note that when we are sending the merkle roots, we include it in withdrawn_balance
    # Filter slots that has a proposer indice with the one
    resulting_slots: list[tuple] = filter_slots_by_proposer(slot_num)
    indexed_fees: list[tuple] = multithread(compute_recipient_fee, resulting_slots)

    total_profits_by_proposer: dict = defaultdict(int)
    for proposer_index, profit in indexed_fees:
        total_profits_by_proposer[proposer_index] += profit

    increase_fee_recipient_balances(total_profits_by_proposer)

    thefts: list[tuple] = multithread(detect_theft, resulting_slots)

    # This will remove any None results, then transpose the list of tuples into a list
    # that is containing 2 list: fee_thefts & proofs
    transposed_thefts = list(map(list, zip(*list(filter(None, thefts)))))

    if thefts:
        handle_regulate_operators(fee_thefts=transposed_thefts[0], proofs=transposed_thefts[1])
