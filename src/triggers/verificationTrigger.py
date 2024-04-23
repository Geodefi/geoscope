from enum import Enum
import pandas as pd

from geode.globals import VALIDATOR_STATE, DEPOSIT_SIZE, GENESIS_FORK_VERSION
from geode.utils.bls.validate import validate_parameters

from ..classes import Trigger
from ..globals.sdk import SDK
from ..globals.events import StakeProposal_sig
from ..globals.constants import (
    MIN_BLOCK_DELAY,
    PENDING_PROPOSALS_THRESHOLD,
    MIN_VERIFICATION_DELAY,
    MAX_VERIFICATION_DELAY,
)

from ..utils.events import get_all_events, decode_abi
from ..utils.portal import stake_params, get_validator
from ..utils.list import find_missing


class ProposalStatus(Enum):
    INVALID = 0
    VALID = 1
    PENDING = 2


class VerificationTrigger(Trigger):
    # Note, this trigger does not utilize checkpoints since it does not seem like verificating that is any easier than populating.
    # Validator state permalink:
    # https://github.com/Geodefi/Portal-Eth/blob/77e4cd18b4133440a7c0729ebfd2fe9cd7fe1aa7/contracts/Portal/globals/validator_state.sol#L7

    __state: dict = {
        "name": "verification_trigger",
        "index": "index",  # validator.index @ PORTAL
        "columns": {
            "pubkey": "str",
            "pool_id": "str",
            # "operator_id",
            # "event_tx",
            "event_block": "uint64",
            # "event_index",
            # "sig1",
            "sig31": "str",
            #  "withdrawal_credential",
            # "state": "uint8",
        },
    }

    def __init__(self):
        Trigger.__init__(
            self,
            structure=self.__state,
            action=self.check_new_validators,
        )

        self.register_verification(self.verify_all_validators)

    def __parse_proposal_events(self, logs: list[list]) -> dict:
        """
        Parse a validator proposal to make compatible with VerificationTrigger.__state.columns

        event: AttributeDict({'address': '0x00', 'blockHash': HexBytes('0x00'), 'blockNumber': 00000, 'data': HexBytes('0x00'), 'logIndex': 00000, 'removed': False, 'topics': [HexBytes('0x00')], 'transactionHash': HexBytes('0x00'), 'transactionIndex': 00000})
        """
        data: dict = {}

        for interval in logs:
            for event in interval:
                if not event.removed:
                    decoded = decode_abi(["uint256", "uint256", "bytes[]"], event.data)
                    for pk in decoded[2]:
                        val = get_validator(pk)
                        data[val.index] = {
                            "pubkey": pk.hex(),
                            "pool_id": str(decoded[0]),
                            # "operator_id": decoded[1],
                            # "event_tx": event.transactionHash,
                            "event_block": event.blockNumber,
                            # "event_index": event.logIndex,
                            "sig31": val.signature31.hex(),
                            # "state": val.state,
                        }

        return data

    def __get_proposal_events(self, first_block: int, last_block: int) -> list:
        """
        Get all the StakeProposal events within the given range : [first_block, last_block]
        Parse for state and return
        """

        logs: list = get_all_events(
            address=SDK.Portal.address,
            signature=StakeProposal_sig,
            first_block=int(first_block),
            last_block=int(last_block),
        )

        return self.__parse_proposal_events(logs)

    def __validate_proposal(self, index: int, last_new_block: int) -> ProposalStatus:
        """
        Validates a proposal as pending/valid/invalid:
        1. Validator's state on Portal is PROPOSED
        2. Validator has only one deposit
        3. It has been more than MIN_BLOCK_DELAY since this deposit
        4. sig1 of this is valid
        5. sig31 of this is valid

        """
        pk = self.state.at[index, "pubkey"]

        # case 1
        val = get_validator(bytes.fromhex(pk))
        if val.state != VALIDATOR_STATE.PROPOSED.value:
            return ProposalStatus.INVALID

        # case 2
        try:
            deposits = SDK.Beacon.get_validator_deposits(pk)
        except:
            return ProposalStatus.PENDING

        if len(deposits) != 1:
            return ProposalStatus.INVALID

        deposit = deposits[0]

        # case 3
        if last_new_block - deposit["block_number"] < MIN_BLOCK_DELAY:
            return ProposalStatus.PENDING

        # get withdrawal credential
        wc = SDK.Portal.pool(int(self.state.at[index, "pool_id"])).withdrawalCredential[
            2:
        ]

        # - sig1
        if not validate_parameters(
            pubkey=pk,
            withdrawal_credentials=wc,
            amount=DEPOSIT_SIZE.PROPOSAL.value,
            signature=deposit["signature"][2:],
            fork_version=GENESIS_FORK_VERSION[SDK.network.value],
        ):
            return ProposalStatus.INVALID

        # - sig31
        if not validate_parameters(
            pubkey=pk,
            withdrawal_credentials=wc,
            amount=DEPOSIT_SIZE.STAKE.value,
            signature=self.state.at[index, "sig31"],
            fork_version=GENESIS_FORK_VERSION[SDK.network.value],
        ):
            return ProposalStatus.INVALID

        return ProposalStatus.VALID

    def __should_update_chain(self, proposals: dict, last_new_block: int) -> bool:
        """
        CONDITIONS:
        1. any validator have been waiting for > MAX_VERIFICATION_DELAY
        OR
        2. has there been > PENDING_PROPOSALS_THRESHOLD validator proposals AND it has been > MIN_VERIFICATION_DELAY since the last proposal
        """

        indices = proposals.keys()
        event_blocks = self.state.loc[indices, "event_block"]

        first_proposal = min(event_blocks)
        if last_new_block >= first_proposal + MAX_VERIFICATION_DELAY:
            return True

        last_proposal = max(event_blocks)
        if last_new_block >= last_proposal + MIN_VERIFICATION_DELAY:
            if len(indices) >= PENDING_PROPOSALS_THRESHOLD:
                return True

        return False

    def __update_chain(self, validations: dict):
        """
        TODO_task_now
        1. call updateVerificationIndex
        2. send update as an email + telegram message
        """

        # Surely, there is at least one pending validator
        for key, val in validations.items():
            if val != ProposalStatus.PENDING:
                new_index = key
        assert new_index != 0

        invalid_array = [
            key for key, val in validations.items() if val == ProposalStatus.INVALID
        ]

    def __update_verification_index(self, changes: dict[dict]) -> tuple:
        """
        changes = {blockNumber: {column: data}}
        Get the new proposals within the scoped blocks
        Check for missing validators and fix if any
        Check for pending proposals and act on it by sending a tx if needed!
        """
        # 1. UPDATE INTERNAL STATE with new proposals

        blocks = changes.keys()

        first_new_block = min(blocks)
        last_new_block = max(blocks)
        first_new_block = 9000000  # TODO_finally delete this line
        last_new_block = 10114834  # TODO_finally delete this line

        new_validators = self.__get_proposal_events(first_new_block, last_new_block)
        self.update_many(new_validators)

        # 2. Make sure there are no missing indices
        missing_indices = find_missing(self.state.index.values.tolist())
        for v in missing_indices:
            # if any, scan the blocks between the gap
            missing_validators = self.__get_proposal_events(
                self.state.at[int(v) - 1, "event_block"],
                self.state.at[int(v) + 1, "event_block"],
            )
            self.update_many(missing_validators)

        # WE ARE DONE WITH THE STATE

        # 1. check all validators since the last verification index
        # why not only the changes? there can be pending validators, since we do not run it.
        params = stake_params(max(blocks))
        validators_index: int = params.validatorsIndex
        verification_index: int = params.verificationIndex

        pending_proposals: dict = {}
        for i in range(verification_index, validators_index + 1):
            pending_proposals[i] = self.__validate_proposal(i, last_new_block)

        # 2. CHECK conditions and execute an update if needed
        if self.__should_update_chain(pending_proposals, last_new_block):
            self.__update_chain(pending_proposals)

        return pending_proposals, last_new_block

    def __check_new_proposals(self, last_block: int) -> bool:
        """
        Check if there are any new proposals by comparing the validatorsIndex to verificationIndex
        """

        params = stake_params(last_block)
        validator = params.validatorsIndex
        verification = params.verificationIndex
        # verification = 0  # TODO_finally fix this

        return validator != verification

    def check_new_validators(self, changes: dict) -> None:
        """
        The action! Check for new proposals, update if triggered.
        """
        if self.__check_new_proposals(max(changes.keys())):
            self.__update_verification_index(changes)

    def __validate_validator(self, val_index: str, validator: dict) -> bool:
        """
        Validates a validator within the state
        """
        # 1. might not be present
        if val_index not in self.state.index:
            return False

        # 2. pubkey might be wrong
        if self.state.at[val_index, "pubkey"] != validator["pubkey"]:
            return False

        # 3. pool_id might be wrong
        if self.state.at[val_index, "pool_id"] != validator["pool_id"]:
            return False

        # 4. event_block might be wrong
        if self.state.at[val_index, "event_block"] != validator["event_block"]:
            return False

        # 5. sig31 might be wrong
        if self.state.at[val_index, "sig31"] != validator["sig31"]:
            return False

        return True

    def verify_all_validators(
        self,
        block_daemon_state: pd.DataFrame,
        mode: str = "alert",
    ):
        """
        Verification function, verifies the current state.
        Does not care about updating the verification index.
        """

        first_block = block_daemon_state.index.min()
        last_block = block_daemon_state.index.max()

        all_validators: dict = self.__get_proposal_events(first_block, last_block)

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
