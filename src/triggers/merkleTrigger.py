from itertools import repeat
from geode.globals import DEPOSIT_SIZE
from geode.utils.wrappers import httpRequest
from geode.utils.merkle import StandartMerkleTree
from ..utils.chain import get_epoch
from ..classes import Trigger
from ..globals.config import CONFIG
from ..globals.sdk import SDK
from ..globals.events import Stake_sig
from ..globals.constants import (
    BEACON_DENOMINATOR,
    ETHER_DENOMINATOR,
    MAX_MERKLE_DELAY_SECONDS,
    PRICE_CHANGE_THRESHOLD_PERCENTAGE,
)
from ..utils.multithread import multithread, multithread
from ..utils.events import get_all_events, decode_abi
from ..utils.portal import stake_params, get_validator, get_all_pool_ids
import pandas as pd

# @httpRequest
# def get_block_beaconchain(block: int):
#     return SDK.Beacon.api_base + f"execution/block/{block}" + SDK.Beacon.api_suffix


def process_fee(block: int):
    pass
    # # b = get_block_beaconchain(block)[0]
    # return {
    #     "proposer": b["posConsensus"]["proposerIndex"],
    #     "reward": b["producerReward"],
    # }


def process_beacon_balance(pubkey: str, current_epoch: str) -> dict:
    # THERE CAN BE 2 TYPE OF VALIDATORS HERE:
    #
    # 1. Deposited 31 eth, have not been reflected yet : beacon.status = deposited, pending:
    # -> beacon(validator).balance is 1 eth.
    # -> safe to assume 31 eth is still on the way.
    #
    # 2. Deposited and processed the 31 eth : any other status
    # -> utilize beacon(validator).balance
    # -> check if slashed or exited : then beacon_balance is assumed to be ZERO !important

    v = SDK.Beacon.get_validator(pubkey)
    status = v["status"]
    balance = v["balance"]
    # withdrawn = v.total_withdrawals

    if status == "deposited":
        assert balance == DEPOSIT_SIZE.PROPOSAL.value / BEACON_DENOMINATOR
        balance = DEPOSIT_SIZE.STAKE.value / BEACON_DENOMINATOR

    elif status == "pending":
        assert balance == DEPOSIT_SIZE.STAKE.value / BEACON_DENOMINATOR

    elif (status == "slashed") or (status == "exited"):
        assert current_epoch >= v["exitepoch"]
        if current_epoch >= v["withdrawableepoch"]:
            balance = 0

    return {"beacon_balance": balance}


def calc_price(id: str, balances: dict):
    pool = SDK.Portal.pool(int(id))
    # TODO_task: TAKE THE LATEST GIVEN BLOCK WHEN CALCULATING
    surplus = pool.surplus
    # TODO_task: TAKE THE LATEST GIVEN BLOCK WHEN CALCULATING
    secured = pool.secured
    # TODO_task: TAKE THE LATEST GIVEN BLOCK WHEN CALCULATING
    supply = SDK.Token.contract.functions.totalSupply(int(id)).call()
    price = (
        (
            (
                balances["beacon_balance"]
                + balances["withdrawn_balance"]
                + balances["fee_recipient_balance"]
            )
            * BEACON_DENOMINATOR
            + (surplus + secured)
        )
        * ETHER_DENOMINATOR
    ) // supply

    return price


def confirm_price_change(id: int, price) -> bool:
    curr_price = SDK.Token.contract.functions.pricePerShare(int(id)).call()
    max_price = (
        int(curr_price) * int(100 + int(PRICE_CHANGE_THRESHOLD_PERCENTAGE))
    ) // int(100)
    return price >= max_price


class MerkleTrigger(Trigger):
    # does not track the validator proposals, just active/exited.
    __state: dict = {
        "name": "merkle_trigger",
        "index": "pubkey",
        "columns": {
            "proposer_index": "uint64",
            "pool_id": "str",
            "withdrawal_contract": "str",
            "event_block": "uint64",
            "beacon_balance": "uint64",  # no need to keep this actually
            "withdrawn_balance": "uint64",
            "fee_recipient_balance": "uint64",  # this tends to get huge (1e18, others are 1e9), so it will probably fail at some point.
        },
    }

    def __init__(self):
        Trigger.__init__(
            self,
            structure=self.__state,
            action=self.update_validators,
        )

        self.register_verification(self.verify_all_validators)

    def __parse_stake_events(self, logs: list[list]) -> dict:
        # logs: [[event][event]]

        data: dict = {}
        for interval in logs:
            for event in interval:
                if not event.removed:
                    decoded = decode_abi(["bytes[]"], event.data)
                    for pk in decoded[0]:
                        val = get_validator(pk)
                        pk = pk.hex()
                        index = SDK.Beacon.get_validator(pk)["validatorindex"]
                        wc = SDK.Portal.pool(val.poolId).withdrawalContract
                        data[pk] = {
                            "proposer_index": index,
                            "pool_id": val["poolId"],
                            "withdrawal_contract": wc,
                            "event_block": event.blockNumber,
                            "beacon_balance": int(0),
                            "withdrawn_balance": int(0),
                            "fee_recipient_balance": int(0),
                        }

        return data

    def __get_stake_events(self, first_block: int, last_block: int) -> dict:
        logs: list = get_all_events(
            address=SDK.Portal.address,
            signature=Stake_sig,
            first_block=int(first_block),
            last_block=int(last_block),
        )

        return self.__parse_stake_events(logs)

    def add_fresh_stake(self, first_block: int, last_block: int):
        # check if there are new validators
        fresh_validators = self.__get_stake_events(first_block, last_block)
        self.update_many(fresh_validators, sort=False)

    def __update_beacon_balances(self, pk_list: list):
        epoch = get_epoch()["epoch"]
        beacon_balances = multithread(
            process_beacon_balance, pk_list, repeat(epoch)
        )
        if beacon_balances:
            self.update_many(dict(zip(pk_list, beacon_balances)), sort=False)

    def __calc_withdrawn_balances(self, blocks: list, indices: list) -> dict:
        # calculates withdrawn balances for given indices, within given blocks

        bals = {}
        for b in blocks:
            for w in b["withdrawals"]:
                i = w["validatorIndex"]
                if i in indices:
                    bals[i] = bals.get(i, 0) + w["amount"]

        return bals

    def update_withdrawn_balances(
        self, blocks: dict, val_indices: list
    ) -> dict:
        withdrawn_balances: dict = self.__calc_withdrawn_balances(
            list(blocks.values()), val_indices
        )

        # for b in blocks.values():
        #     for w in b["withdrawals"]:
        #         i = w["validatorIndex"]
        #         if i in withdrawn_balances.index:
        #             withdrawn_balances.at[i, "withdrawn_balance"] += w["amount"]

        # TODO: instead of update, find a way to ADD : ez.
        return withdrawn_balances
        # self.update_many(
        #     withdrawn_balances.to_dict(),
        #     sort=False,
        #     as_index="proposer_index",
        # )

    def __update_fee_recipient_balances(
        self,
        blocks: dict,
        proposer_indices: list,
    ):
        # # process fee => get proposer, if ours check the producerReward to the fee_recipient_balance
        # block_proposers = multithread(
        #     process_fee, blocks
        # )  # TODO_task: yes, change process_fee' logic...

        # # detect the blocks with fee recipient.

        # produced_blocks = [
        #     b for b in block_proposers if b["proposer"] in proposer_indices
        # ]

        # for b in produced_blocks:
        #     self.state.loc[
        #         self.state["proposer_index"] == b["proposer"], "fee_recipient_balance"
        #     ] += b["reward"]
        pass

    def __calc_prices(self) -> dict:
        ids: list = get_all_pool_ids()

        balances = [
            {
                "beacon_balance": int(
                    self.state.loc[
                        self.state["pool_id"] == id, "beacon_balance"
                    ].sum()
                ),
                "withdrawn_balance": int(
                    self.state.loc[
                        self.state["pool_id"] == id,
                        "withdrawn_balance",
                    ].sum()
                ),
                "fee_recipient_balance": int(
                    self.state.loc[
                        self.state["pool_id"] == id,
                        "fee_recipient_balance",
                    ].sum()
                ),
            }
            for id in ids
        ]
        prices = multithread(calc_price, ids, balances)
        return dict(zip(ids, prices))

    def __should_update_chain(
        self, prices: dict, effective_timestamp: int
    ) -> bool:
        # Validators:
        # TODO_finally ?
        #
        # Price:
        # - 24h (block) passed since the last update
        # - price changes >1% for a pool
        last_update = stake_params().oracleUpdateTimestamp

        if effective_timestamp > last_update + MAX_MERKLE_DELAY_SECONDS:
            return True

        confirmations = multithread(
            confirm_price_change, prices.keys(), prices.values()
        )
        return any(confirmations)

    def __update_chain(self, prices: dict):
        # TODO_task_now
        num_val = get_epoch()["validatorscount"]

        # id, price
        price_leaves = list(map(list, prices.items()))
        # merkle_prices = StandartMerkleTree().of(
        #     values=price_leaves, types=["uint256", "uint256"]
        # )

        # pubkey, beacon_balance, withdrawn_balance
        x = self.state["beacon_balance"].to_dict()
        y = (
            self.state["withdrawn_balance"]
            + self.state["fee_recipient_balance"]
        ).to_dict()

        balance_leaves = [[id, x[id], y[id]] for id, p in x.items()]
        # merkle_balances = StandartMerkleTree().of(
        #     values=balance_leaves, types=["bytes", "uint256", "uint256"]
        # )

        # print(price_leaves)
        # print(balance_leaves)

    def update_validators(self, changes: dict):
        blocks = changes.keys()
        self.add_fresh_stake(min(blocks), max(blocks))

        pk_list = self.state.index.tolist()
        self.__update_beacon_balances(pk_list)

        proposer_indices = self.state["proposer_index"]  # .unique()
        self.update_withdrawn_balances(changes, proposer_indices)

        # TODO_task: rate limit... find another way.
        self.__update_fee_recipient_balances(blocks, proposer_indices)

        # WE ARE DONE WITH THE STATE
        prices = self.__calc_prices()
        effective_ts = max(changes.values(), key=lambda x: x["timestamp"])[
            "timestamp"
        ]
        if self.__should_update_chain(prices, effective_ts):
            self.__update_chain(prices)

    def __validate_validator(self, val_index: str, validator: dict) -> bool:
        # 1. might not be present
        if val_index not in self.state.index:
            return False

        # 2. proposer_index might be wrong
        if True:
            return False

        # 3. pool_id might be wrong
        if True:
            return False

        # 4. withdrawal_contract might be wrong
        if True:
            return False

        # 5. event_block might be wrong
        if True:
            return False

        # 6. withdrawn_balance might be wrong
        if True:
            return False

        return True

    def verify_all_validators(
        self,
        block_daemon_state: pd.DataFrame,
        mode: str = "alert",
    ):
        # todo_task_now : might need to try somrthing different
        first_block = block_daemon_state.index.min()
        last_block = block_daemon_state.index.max()

        all_validators = self.__get_stake_events(first_block, last_block)

        for val_index, validator in all_validators.items():
            is_valid = self.__validate_validator(val_index, validator)

            if not is_valid:
                if mode == "fix":
                    self.update(val_index, validator)

                elif mode == "alert":
                    # todo: send notification and continue
                    raise

                elif mode == "quit":
                    # todo: send notification and quit
                    raise

        pass
