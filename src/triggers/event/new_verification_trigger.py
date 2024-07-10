# -*- coding: utf-8 -*-

from geodefi.globals import VALIDATOR_STATE, DEPOSIT_SIZE, GENESIS_FORK_VERSION
from geodefi.utils.bls.validate import validate_parameters

from src.classes import Trigger
from src.logger import log
from src.globals import SDK, MIN_BLOCK_DELAY

from src.helpers import (
    fetch_unverified_vals,
    create_stake_proposal_table,
    create_validators_table,
    update_geonius_verification_pks,
)
from src.actions import call_updateVerificationIndex


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
        new_verification_index = None
        for pk, index, pool_id, sig31, wc in vals:
            status = self.validate_proposal(
                pk, pool_id, sig31, wc, current_block_ts
            )

            if status == 0:
                invalid_pks.append(pk)
            elif status == 1:
                valid_pks.append(pk)
                new_verification_index = index
                len_pending_pks_when_index_set = len(pending_pks)
            elif status == 2:
                pending_pks.append(pk)

        # adding the pending pks to invalid pks that were still pending when larger index was verified
        invalid_pks.extend(pending_pks[:len_pending_pks_when_index_set])

        return new_verification_index, valid_pks, invalid_pks

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
        MAX_VERIFICATION_DELAY = 24 * 60 * 60  # 24 hours
        MIN_VERIFICATION_DELAY = 6 * 60 * 60  # 6 hour
        PENDING_PROPOSALS_THRESHOLD = 10

        # TODO: from db fetch all vals that are ready to be verified on chain
        #       select smallest timestamp and largest timestamp to check below and return true if any of the conditions are met
        #       also fetch the number of pending proposals to be verified

        earliest_ts = 0  # fetch from db
        if current_block_ts >= earliest_ts + MAX_VERIFICATION_DELAY:
            return True

        latest_ts = 9999  # fetch from db
        if current_block_ts >= latest_ts + MIN_VERIFICATION_DELAY:
            valid_proposal_count = 3  # fetch from db
            if valid_proposal_count >= PENDING_PROPOSALS_THRESHOLD:
                return True

        return False

    def check_new_validators(self, *args, **kwargs) -> None:
        """The action! Check for new proposals, update if triggered.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """

        # if self.__check_new_proposals(fetch_unverified_pks()):
        #     self.__update_verification_index(changes)

        # data is already sorted according to increasing order of portal_index
        # fetch pubkey, portal_index, pool_id, signature31 in this order from the db --> need to handle sig1 at some point
        vals: list[tuple] = fetch_unverified_vals()

        current_block_ts = SDK.w3.eth.get_block("latest")["timestamp"]

        new_verification_index, valid_pks, invalid_pks = (
            self.validate_proposals(vals, current_block_ts)
        )

        update_geonius_verification_pks(valid_pks, "valid")
        update_geonius_verification_pks(invalid_pks, "invalid")

        # TODO: fetch invalid pks from db and max verification index from db

        current_verification_index = 1  # fetch from db
        # if there is no new verification index, then the new verification index is the same as the current one
        if new_verification_index is None:
            new_verification_index = current_verification_index

        # TODO: should update chain check should be implemented for MAX_VERIFICATION_DELAY and PENDING_PROPOSALS_THRESHOLD, MIN_VERIFICATION_DELAY
        # TODO: if deposits are fetched somehow, then save timestamp/slot for them and check from that time

        is_valid_to_push = False
        if len(invalid_pks) == 0:
            is_valid_to_push = self.should_update_chain(current_block_ts)

        if is_valid_to_push:
            call_updateVerificationIndex(new_verification_index, invalid_pks)
