# -*- coding: utf-8 -*-

from multiproof import StandardMerkleTree
from web3.exceptions import ContractLogicError

from src.classes import Trigger
from src.globals import get_constants, get_logger
from src.helpers.slots import fetch_slots_batch
from src.helpers.withdrawals import filter_withdrawals_batch, process_many_withdrawals
from src.helpers.deposits import filter_deposits_batch, process_many_deposits
from src.database.slots import insert_many_slots, get_max_slot
from src.database.deposits import insert_many_deposits
from src.database.withdrawals import insert_many_withdrawals
from src.database.validators import update_portal_validators, fetch_validator_balances
from src.actions.multisig import send_tx


class BeaconTrigger(Trigger):
    """Processes updates from both execution and consensus chain for all slots between
        the configured start slot and the latest periodically detected slot.

    Attributes:
        name (str): name of the trigger to be used when logging etc. (value: BEACON)
    """

    name: str = "BEACON"

    def __init__(self) -> None:
        """Initializes a BeaconTrigger object.
        The trigger will process the changes of the daemon after a loop.
        It is a callable object. It is used to process the changes of the daemon.
        It can only have 1 action:
            indexing all slots between the configured start slot
            and the latest periodically detected slot.
        """

        Trigger.__init__(self, name=self.name, action=self.index_slots)

    def index_slots(self, curr_slot_num, *args) -> None:
        """
        1. Indexes and saves all required slot data to db
            - do it once! (unless db is wiped out with '--reset' flag)
            - can restore from db in case of a restart.
        2. fetches and saves validator data from portal
        3. processes deposits, filters according to the portal and saves.
        4. processes withdrawals, filters according to the portal and saves.
        5. updates validator states from beaconchain
        6. updates validator balances from beaconchain
        """
        fallback_slot: int = int(get_constants().chain.start.slot)
        db_slot_num: int = get_max_slot(fallback_slot)

        slot_process_steps: int = 10000
        for i in range(db_slot_num, curr_slot_num + 1, slot_process_steps):
            # Processing slots in batches, we can not just try to do it at once!
            last_slot_num: int = min(i + slot_process_steps, curr_slot_num)
            # So, since we are getting the latest processed slot here, we should actually **SAVE** it at the
            # last point where we are done processing the validators, deposits and withdrawals.
            gathered_slots = fetch_slots_batch(first_slot=i, last_slot=last_slot_num)

            update_portal_validators(
                first_block=gathered_slots[0]["block_number"],
                last_block=gathered_slots[-1]["block_number"],
            )

            deposits: list[dict] = filter_deposits_batch(gathered_slots)
            if deposits:
                process_many_deposits(curr_slot_num, deposits)
                insert_many_deposits(deposits)

            withdrawals: list[dict] = filter_withdrawals_batch(gathered_slots)
            if withdrawals:
                process_many_withdrawals(withdrawals)
                insert_many_withdrawals(withdrawals)

            # TODO: process slots and update fee_recipient balances here...
            # Note that when we are sending the merkle roots, we include it in withdrawn_balance

            insert_many_slots(gathered_slots)

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
        all_val_count = 50_000  # we can fetch if from oklink, but need to discuss this
        if all_val_count < 50_000:
            all_val_count = 50_000  # minimum count for the merkle tree

        # ----- send tx to multisig to update chain -----
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

        # Now we can see if we need to do any actions here!
        # What a rush, huh.
