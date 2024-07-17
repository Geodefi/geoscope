# -*- coding: utf-8 -*-

from geodefi.globals import VALIDATOR_STATE, DEPOSIT_SIZE, GENESIS_FORK_VERSION
from geodefi.utils.bls.validate import validate_parameters

from src.classes.trigger import Trigger
from src.globals.sdk import SDK
from src.globals.constants import (
    MIN_BLOCK_DELAY,
    MIN_VERIFICATION_DELAY,
    MAX_VERIFICATION_DELAY,
    PENDING_PROPOSALS_THRESHOLD,
)
from src.helpers.db_validators import (
    fetch_unverified_vals,
    create_validators_table,
    update_geoscope_verification_pks,
    update_geoscope_verification_state,
    fetch_valid_val_count,
    fetch_min_max_ts,
    fetch_new_verification_index,
    fetch_invalid_pks,
)
from src.helpers.db_events import create_stake_proposal_table
from src.helpers.portal import get_StakeParams
from src.actions.portal import call_updateVerificationIndex
from src.logger import log


# TODO: this wont be an event trigger, will be a block trigger, need to move it
class NewVerificationTrigger(Trigger):
    """Every day checks for proposed validators.

    Attributes:
        name (str): name of the trigger to be used when logging etc. (value: VERIFICATION)
    """

    name: str = "VERIFICATION"

    def __init__(self) -> None:
        """Initializes a VerificationTrigger object. The trigger will process the changes of the daemon after a loop.
        It is a callable object. It is used to process the changes of the daemon. It can only have 1 action.
        """

        Trigger.__init__(self, name=self.name, action=self.check_new_validators)
        create_validators_table()
        create_stake_proposal_table()
        log.debug(f"{self.name} is initated.")

    def validate_proposals(
        self, vals: list[tuple], current_block_ts: int
    ) -> tuple:
        """
        Validates the proposals of the validators.
        Args:
            pks (list): List of public keys of the validators.
            indexes (list): List of indexes of the validators.

        Returns:
            tuple: Tuple of new verification index and invalid public keys.
        """

        valid_pks = []
        invalid_pks = []
        pending_pks = []
        len_pending_pks_when_index_set = 0
        for pk, pool_id, sig31, wc in vals:
            status = self.validate_proposal(
                pk, pool_id, sig31, wc, current_block_ts
            )
            if status == 0:
                invalid_pks.append(pk)
            elif status == 1:
                valid_pks.append(pk)
                len_pending_pks_when_index_set = len(pending_pks)
            elif status == 2:
                pending_pks.append(pk)

        # adding the pending pks to invalid pks that were still pending when larger index was verified
        invalid_pks.extend(pending_pks[:len_pending_pks_when_index_set])

        return valid_pks, invalid_pks

    def validate_proposal(
        self, pk: str, pool_id: str, sig31: str, wc: str, current_block_ts: int
    ) -> int:
        """
        Validates a proposal as pending/valid/invalid:
        1. Validator's state on Portal is PROPOSED
        2. Validator has only one deposit
        3. It has been more than MIN_BLOCK_DELAY since this deposit
        4. sig1 of this is valid
        5. sig31 of this is valid

        Args:
            pk (str): Public key of the validator.
            pool_id (str): Pool ID of the validator.
            sig31 (str): Signature 31 of the validator.
            wc (str): Withdrawal credentials of the validator. (comes from beacon chain)

        Returns:
            int: Proposal status. (0: invalid, 1: valid, 2: pending)
        """

        val = SDK.portal.validator(pk)
        pool = SDK.portal.pool(int(pool_id))

        # case 1
        if val.state != VALIDATOR_STATE.PROPOSED:
            return 0

        # case 2
        # TODO: instead of last_new_block, fetch the current block number??
        if current_block_ts - deposit["block_number"] < MIN_BLOCK_DELAY:
            return 2

        # get withdrawal credential of pool from Portal
        pool_wc = pool.withdrawalCredential

        # case 3
        if not (
            val.balance == 1e9
            and val.withdrawal_credentials == wc  # wc is same on beacon chain
            and wc == pool_wc  # correct wc is given to beacon chain
        ):
            return 0

        # - sig31
        if not validate_parameters(
            pubkey=pk[2:],
            withdrawal_credentials=pool_wc[2:],
            amount=DEPOSIT_SIZE.STAKE,
            signature=sig31[2:],
            fork_version=GENESIS_FORK_VERSION[SDK.network.value],
        ):
            return 0

        return 1

    def should_update_chain(self, current_block_ts: int) -> bool:
        """
        CONDITIONS:
        1. any validator have been waiting for > MAX_VERIFICATION_DELAY
        OR
        2. has there been > PENDING_PROPOSALS_THRESHOLD validator proposals AND it has been > MIN_VERIFICATION_DELAY since the last proposal
        """

        earliest_ts, latest_ts = fetch_min_max_ts()

        if current_block_ts >= earliest_ts + MAX_VERIFICATION_DELAY:
            return True

        if current_block_ts >= latest_ts + MIN_VERIFICATION_DELAY:
            valid_pending_count: int = fetch_valid_val_count()
            if valid_pending_count >= PENDING_PROPOSALS_THRESHOLD:
                return True

        return False

    def check_new_validators(self, *args, **kwargs) -> None:
        """The action! Check for new proposals, update if triggered.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """

        # data is already sorted according to increasing order of portal_index
        # fetch pubkey, portal_index, pool_id, signature31 in this order from the db
        vals: list[tuple] = fetch_unverified_vals()

        current_block_ts = SDK.w3.eth.get_block("latest")["timestamp"]

        valid_pks, invalid_pks = self.validate_proposals(vals, current_block_ts)

        update_geoscope_verification_pks(valid_pks, "valid")
        update_geoscope_verification_pks(invalid_pks, "invalid")

        # fetch invalid pks from db
        invalid_pks = fetch_invalid_pks()

        # TODO: if deposits are fetched somehow, then save timestamp/slot for them and check from that time
        is_valid_to_push = self.should_update_chain(current_block_ts)

        if is_valid_to_push or len(invalid_pks) > 0:
            # max verification index from db
            new_verification_index: int = fetch_new_verification_index()
            if new_verification_index is None:
                # get current index as new index
                new_verification_index: int = get_StakeParams()[4]
            call_updateVerificationIndex(new_verification_index, invalid_pks)

            # update db
            update_geoscope_verification_state(
                "onchain", "valid", new_verification_index
            )
            update_geoscope_verification_state("onchain", "invalid")
