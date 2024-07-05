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

    def validate_proposals(self, vals: list[tuple]) -> tuple:
        """
        Validates the proposals of the validators.
        Args:
            pks (list): List of public keys of the validators.
            indexes (list): List of indexes of the validators.

        Returns:
            tuple: Tuple of new verification index and invalid public keys.
        """

        invalid_pks = []
        for pk, index, pool_id, sig31 in vals:
            status = self.validate_proposal(pk, pool_id, sig31)

            if status == 0:
                invalid_pks.append(pk)
            elif status == 1:
                new_verification_index = index
            elif status == 2:
                # TODO: what to do with pending proposals? Is it possible for a bigger index to be not pending? I hope not.
                break

        return new_verification_index, invalid_pks

    def validate_proposal(self, pk: str, pool_id: str, sig31: str) -> int:
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

        Returns:
            int: Proposal status. (0: invalid, 1: valid, 2: pending)
        """

        val = SDK.portal.validator(pk)

        # case 1
        if val.state != VALIDATOR_STATE.PROPOSED:
            return 0

        # case 2
        try:
            # TODO: check if this is the correct way to get deposits
            deposits = SDK.beacon.beacon_deposit_snapshot(pk)
        except Exception as e:
            # TODO: it may not be pending, but failed to get deposits
            #       need to check if it is pending or not some other way
            log.error(
                f"Failed to get deposits for {pk} (probably pending): {e}"
            )
            return 2

        if len(deposits) != 1:
            return 0

        deposit = deposits[0]

        # case 3
        # TODO: instead of last_new_block, fetch the current block number??
        if last_new_block - deposit["block_number"] < MIN_BLOCK_DELAY:
            return 2

        # get withdrawal credential
        wc = SDK.portal.pool(int(pool_id)).withdrawalCredential[2:]

        # - sig1
        if not validate_parameters(
            pubkey=pk[2:],
            withdrawal_credentials=wc[2:],
            amount=DEPOSIT_SIZE.PROPOSAL,
            signature=sig1[
                2:
            ],  # deposit["signature"][2:],  # TODO: get sig1 from db here or fetch beforehand and pass it as an argument?
            fork_version=GENESIS_FORK_VERSION[SDK.network.name],
        ):
            return 0

        # - sig31
        if not validate_parameters(
            pubkey=pk[2:],
            withdrawal_credentials=wc[2:],
            amount=DEPOSIT_SIZE.STAKE,
            signature=sig31[2:],
            fork_version=GENESIS_FORK_VERSION[SDK.network.value],
        ):
            return 0

        return 1

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

        new_verification_index, invalid_pks = self.validate_proposals(vals)

        # TODO: should update chain check should be implemented for MAX_VERIFICATION_DELAY and PENDING_PROPOSALS_THRESHOLD, MIN_VERIFICATION_DELAY

        call_updateVerificationIndex(new_verification_index, invalid_pks)
