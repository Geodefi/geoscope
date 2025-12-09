"""
Functions to manage the Validators table in the database.
"""

from typing import Any

from web3.types import BlockIdentifier

from src.classes import Database
from src.common import BigInteger
from src.database.utils.generators import (
    Condition,
    generate_create_table_sql,
    generate_drop_table_sql,
    generate_insert_sql,
    generate_select_exists_sql,
    generate_select_fields_sql,
    generate_select_fields_where_conditions_sql,
    generate_select_fields_where_in_sql,
    generate_update_where_conditions_sql,
)
from src.exceptions.classes.database import DatabaseError, DatabaseMismatchError
from src.globals import get_logger
from src.globals.constants.database import (
    VALIDATORS_BEACON_INDEX_FIELD,
    VALIDATORS_EXIT_EPOCH_FIELD,
    VALIDATORS_FEE_RECIPIENT_BALANCE_FIELD,
    VALIDATORS_INFRASTRUCTURE_FEE_FIELD,
    VALIDATORS_LAST_WITHDRAWN_FIELD,
    VALIDATORS_OPERATOR_FEE_FIELD,
    VALIDATORS_OPERATOR_ID_FIELD,
    VALIDATORS_POOL_FEE_FIELD,
    VALIDATORS_POOL_ID_FIELD,
    VALIDATORS_PORTAL_INDEX_FIELD,
    VALIDATORS_PROPOSAL_SIGNATURE_FIELD,
    VALIDATORS_PROPOSAL_SLOT_FIELD,
    VALIDATORS_PUBKEY_FIELD,
    VALIDATORS_SIGNATURE31_FIELD,
    VALIDATORS_STAKE_SIGNATURE_FIELD,
    VALIDATORS_TABLE_KEY,
    VALIDATORS_WITHDRAWAL_CREDENTIALS_FIELD,
    VALIDATORS_WITHDRAWN_BALANCE_FIELD,
)
from src.helpers.portal import fetch_verification_index
from src.utils.notify import send_email

# Pre-rendered SQL Statements
CREATE_TABLE_SQL: str = generate_create_table_sql(VALIDATORS_TABLE_KEY)
DROP_TABLE_SQL: str = generate_drop_table_sql(VALIDATORS_TABLE_KEY)
INSERT_SQL: str = generate_insert_sql(VALIDATORS_TABLE_KEY, only_not_null_fields=True)
SELECT_VALIDATOR_BALANCES_SQL: str = generate_select_fields_sql(
    VALIDATORS_TABLE_KEY,
    VALIDATORS_PUBKEY_FIELD,
    VALIDATORS_WITHDRAWN_BALANCE_FIELD,
    VALIDATORS_FEE_RECIPIENT_BALANCE_FIELD,
)
SELECT_VALIDATORS_BY_POOL_SQL: str = generate_select_fields_where_conditions_sql(
    VALIDATORS_TABLE_KEY,
    [Condition(field=VALIDATORS_POOL_ID_FIELD, operator="=")],
    VALIDATORS_PUBKEY_FIELD,
    VALIDATORS_POOL_FEE_FIELD,
    VALIDATORS_OPERATOR_FEE_FIELD,
    VALIDATORS_INFRASTRUCTURE_FEE_FIELD,
    VALIDATORS_WITHDRAWN_BALANCE_FIELD,
    VALIDATORS_LAST_WITHDRAWN_FIELD,
    VALIDATORS_FEE_RECIPIENT_BALANCE_FIELD,
)
SELECT_OPERATOR_ID_BY_BEACON_INDEX_SQL = generate_select_fields_where_conditions_sql(
    VALIDATORS_TABLE_KEY,
    [Condition(field=VALIDATORS_BEACON_INDEX_FIELD, operator="=")],
    VALIDATORS_OPERATOR_ID_FIELD,
)
CHECK_VALIDATOR_PUBKEY_EXISTS_SQL = generate_select_exists_sql(
    VALIDATORS_TABLE_KEY, VALIDATORS_PUBKEY_FIELD
)

CHECK_VALIDATOR_BEACON_INDEX_EXISTS_SQL = generate_select_exists_sql(
    VALIDATORS_TABLE_KEY, VALIDATORS_BEACON_INDEX_FIELD
)
SELECT_PROPOSED_VALIDATORS_SQL = generate_select_fields_where_conditions_sql(
    VALIDATORS_TABLE_KEY,
    [
        Condition(field=VALIDATORS_PROPOSAL_SIGNATURE_FIELD, operator="IS NOT NULL"),
        Condition(field=VALIDATORS_PORTAL_INDEX_FIELD, operator=">"),
    ],
    VALIDATORS_PUBKEY_FIELD,
    VALIDATORS_PORTAL_INDEX_FIELD,
    VALIDATORS_POOL_ID_FIELD,
    VALIDATORS_SIGNATURE31_FIELD,
    VALIDATORS_WITHDRAWAL_CREDENTIALS_FIELD,
    VALIDATORS_PROPOSAL_SIGNATURE_FIELD,
    VALIDATORS_STAKE_SIGNATURE_FIELD,
    VALIDATORS_PROPOSAL_SLOT_FIELD,
)
SELECT_SIGNATURES_SQL = generate_select_fields_where_conditions_sql(
    VALIDATORS_TABLE_KEY,
    [Condition(field=VALIDATORS_PUBKEY_FIELD, operator="=")],
    VALIDATORS_PROPOSAL_SIGNATURE_FIELD,
    VALIDATORS_STAKE_SIGNATURE_FIELD,
)

# Generate the SQL statement for updating stake_signature
UPDATE_STAKE_SIGNATURE_SQL: str = generate_update_where_conditions_sql(
    VALIDATORS_TABLE_KEY,
    [Condition(field=VALIDATORS_PUBKEY_FIELD, operator="=")],
    VALIDATORS_STAKE_SIGNATURE_FIELD,
)

# Generate the SQL statement for updating other fields
UPDATE_OTHER_FIELDS_SQL: str = generate_update_where_conditions_sql(
    VALIDATORS_TABLE_KEY,
    [Condition(field=VALIDATORS_PUBKEY_FIELD, operator="=")],
    VALIDATORS_PROPOSAL_SIGNATURE_FIELD,
    VALIDATORS_PROPOSAL_SLOT_FIELD,
    VALIDATORS_BEACON_INDEX_FIELD,
    VALIDATORS_WITHDRAWAL_CREDENTIALS_FIELD,
    VALIDATORS_EXIT_EPOCH_FIELD,
)

UPDATE_WITHDRAWN_BALANCE_SQL: str = generate_update_where_conditions_sql(
    VALIDATORS_TABLE_KEY,
    [Condition(field=VALIDATORS_BEACON_INDEX_FIELD, operator="=")],
    VALIDATORS_WITHDRAWN_BALANCE_FIELD,
)
UPDATE_FEE_RECIPIENT_BALANCE_SQL: str = generate_update_where_conditions_sql(
    VALIDATORS_TABLE_KEY,
    [Condition(field=VALIDATORS_BEACON_INDEX_FIELD, operator="=")],
    VALIDATORS_FEE_RECIPIENT_BALANCE_FIELD,
)


def create_validators_table() -> None:
    """
    Creates the Validators table in the database.

    Raises:
        DatabaseError: If there is an error creating the table.
    """
    try:
        with Database() as db:
            db.execute(CREATE_TABLE_SQL)
        get_logger().debug(f"Created table: {VALIDATORS_TABLE_KEY}")
    except Exception as e:
        raise DatabaseError(f"Error creating {VALIDATORS_TABLE_KEY} table") from e


def drop_validators_table() -> None:
    """
    Drops the Validators table from the database.

    Raises:
        DatabaseError: If there is an error dropping the table.
    """
    try:
        with Database() as db:
            db.execute(DROP_TABLE_SQL)
        get_logger().debug(f"Dropped table: {VALIDATORS_TABLE_KEY}")
    except Exception as e:
        raise DatabaseError(f"Error dropping {VALIDATORS_TABLE_KEY} table") from e


def reinitialize_validators_table() -> None:
    """
    Reinitializes the Validators table by dropping and recreating it.

    Raises:
        DatabaseError: If there is an error reinitializing the table.
    """
    try:
        with Database() as db:
            db.execute(DROP_TABLE_SQL)
            db.execute(CREATE_TABLE_SQL)
        get_logger().warning(f"Reinitialized table: {VALIDATORS_TABLE_KEY}")
    except Exception as e:
        get_logger().error(f"Failed to reinitialize {VALIDATORS_TABLE_KEY} table.")
        raise DatabaseError(f"Error reinitializing {VALIDATORS_TABLE_KEY} table") from e


def insert_validators_batch(new_validators: list[dict[str, int | str | BigInteger]]) -> None:
    """
    Inserts a batch of validator records into the Validators table.

    Establishes a connection to the database and executes a parameterized SQL command
    to insert multiple validator records at once.

    Args:
        new_validators (list[dict[str, Any]]): A list of validator records to insert.
        Each dictionary must contain the following fields:
         - VALIDATORS_PUBKEY_FIELD (str) : The public key of the validator.
         - VALIDATORS_PORTAL_INDEX_FIELD (int) : The index of the
             validator on Geodefi Portal.
         - VALIDATORS_POOL_ID_FIELD (BigInteger) : The pool ID.
         - VALIDATORS_OPERATOR_ID_FIELD (BigInteger) : The operator ID.
         - VALIDATORS_POOL_FEE_FIELD (BigInteger) : The fee charged by the pool.
         - VALIDATORS_OPERATOR_FEE_FIELD (BigInteger) : The fee charged by the operator.
         - VALIDATORS_INFRASTRUCTURE_FEE_FIELD (BigInteger) : The infrastructure fee.
         - VALIDATORS_SIGNATURE31_FIELD (str) : Signature saved on Portal,.
              used while staking +31 eth Expected to be same with the stake_signature.

    Raises:
        DatabaseError: If an error occurs while inserting the validators into the Validators table.
    """
    try:
        with Database() as db:
            db.executemany(INSERT_SQL, new_validators)
        get_logger().debug(f"Inserted {len(new_validators)} new validators in Validators table")
    except Exception as e:
        raise DatabaseError("Error inserting many validators into table Validators") from e


def read_operator_id_by_beacon_index(beacon_index: int) -> BigInteger:
    """
    Retrieves the operator ID associated with a given beacon index from the Validators table.

    Args:
        beacon_index (int): The beacon index of the validator.

    Returns:
        BigInteger: The operator ID if found.

    Raises:
        DatabaseError: If there is an error querying the database.
        DatabaseMismatchError: If no operator ID is found for the given beacon index.
    """
    try:
        with Database() as db:
            db.execute(
                SELECT_OPERATOR_ID_BY_BEACON_INDEX_SQL,
                {VALIDATORS_BEACON_INDEX_FIELD: beacon_index},
            )
            result = db.fetchone()
            if result and result[0] is not None:
                return result[0]
            raise DatabaseMismatchError(
                f"No operator ID found for beacon index {beacon_index} \
                in table {VALIDATORS_TABLE_KEY}"
            )
    except Exception as e:
        raise DatabaseError(
            f"Error fetching operator ID with beacon index {beacon_index} \
            from table {VALIDATORS_TABLE_KEY}"
        ) from e


# TODO:(crash) This function is not used, do we delete or keep it?
def read_validator_balances() -> list[tuple[str, BigInteger, BigInteger]]:
    """
    Reads the pubkey and validator cumulative balances (withdrawn and fee recipient)
    from the database.

    Returns:
        list[tuple[str, BigInteger, BigInteger]]:
            A list of tuples where each tuple contains:
                - pubkey (str): The public key of the validator.
                - withdrawn_balance (BigInteger): The amount withdrawn by the validator.
                - fee_recipient_balance (BigInteger): The balance of the fee recipient.

    Raises:
        DatabaseError: If there is an error fetching validators from the Validators table.
    """
    try:
        with Database() as db:
            db.execute(SELECT_VALIDATOR_BALANCES_SQL)
            return db.fetchall()
    except Exception as e:
        raise DatabaseError("Error fetching validator balances from table Validators") from e


def read_validators_by_pool(
    pool_id: BigInteger,
) -> list[tuple[str, BigInteger, BigInteger, BigInteger, BigInteger, BigInteger, BigInteger]]:
    """
    Fetches the required info about the validators of the given pool.

    Args:
        pool_id (BigInteger): The pool ID to fetch the validators for.

    Returns:
        list[tuple[str, BigInteger, BigInteger, BigInteger, BigInteger, BigInteger, BigInteger]]:
            A list of tuples where each tuple contains:
                - pubkey (str): The public key of the validator.
                - pool_fee (BigInteger): The pool fee associated with the validator.
                - operator_fee (BigInteger): The operator fee.
                - infrastructure_fee (BigInteger): The infrastructure fee.
                - withdrawn_balance (BigInteger): The withdrawn balance.
                - last_withdrawn (BigInteger): The epoch or timestamp of the last withdrawal.
                - fee_recipient_balance (BigInteger): The balance of the fee recipient.

    Raises:
        DatabaseError: If there is an error fetching validators from the Validators table.
    """
    try:
        with Database() as db:
            db.execute(
                SELECT_VALIDATORS_BY_POOL_SQL,
                {VALIDATORS_POOL_ID_FIELD: pool_id},
            )
            return db.fetchall()
    except Exception as e:
        raise DatabaseError(
            f"Error fetching validators from pool {pool_id} from table {VALIDATORS_TABLE_KEY}"
        ) from e


def read_proposed_validators(
    block_identifier: BlockIdentifier,
) -> list[tuple[str, int, BigInteger, str, str, str, str, int]]:
    """
    Detects pending validators that are waiting to be approved by Oracle:
        - proposal_signature exists, meaning the proposal deposit was processed.
        - Has higher portal_index than verification_index, meaning its portal_state is PENDING.

    Args:
        block_identifier (str): The identifier for the block to fetch the verification index.

    Returns:
        list[tuple[str, int, BigInteger, str, str, str, str, int]]: List of validators with fields:
            - VALIDATORS_PUBKEY_FIELD (str)
            - VALIDATORS_PORTAL_INDEX_FIELD (int)
            - VALIDATORS_POOL_ID_FIELD (BigInteger)
            - VALIDATORS_SIGNATURE31_FIELD (str)
            - VALIDATORS_WITHDRAWAL_CREDENTIALS_FIELD (str)
            - VALIDATORS_PROPOSAL_SIGNATURE_FIELD (str)
            - VALIDATORS_STAKE_SIGNATURE_FIELD (str)
            - VALIDATORS_PROPOSAL_SLOT_FIELD (int)

    Raises:
        DatabaseError: If there is an error querying the database.
    """
    v_idx: int = fetch_verification_index(block_identifier)
    try:
        with Database() as db:
            db.execute(
                SELECT_PROPOSED_VALIDATORS_SQL,
                {VALIDATORS_PORTAL_INDEX_FIELD: v_idx},
            )
            return db.fetchall()
    except Exception as e:
        raise DatabaseError("Error fetching validators from table Validators") from e


def check_validator_by_pubkey(pubkey: str) -> bool:
    """
    Checks if a given pubkey is saved in the Validators table.

    Args:
        pubkey (str): Public key of the validator.

    Returns:
        bool: True if the public key exists in the database, False otherwise.

    Raises:
        DatabaseError: If there is an error querying the database.
    """
    try:
        with Database() as db:
            db.execute(
                CHECK_VALIDATOR_PUBKEY_EXISTS_SQL,
                {VALIDATORS_PUBKEY_FIELD: pubkey},
            )
            result = db.fetchone()
            return result is not None
    except Exception as e:
        raise DatabaseError(
            f"Error checking if pubkey '{pubkey}' is in table '{VALIDATORS_TABLE_KEY}'"
        ) from e


def check_validator_by_beacon_index(beacon_index: int) -> bool:
    """
    Checks if a given beacon chain index is saved in the Validators table.

    Args:
        beacon_index (int): The beacon index of the validator.

    Returns:
        bool: True if the beacon index exists in the database, False otherwise.

    Raises:
        DatabaseError: If there is an error querying the database.
    """
    try:
        with Database() as db:
            db.execute(
                CHECK_VALIDATOR_BEACON_INDEX_EXISTS_SQL,
                {VALIDATORS_BEACON_INDEX_FIELD: beacon_index},
            )
            result = db.fetchone()
            return result is not None
    except Exception as e:
        raise DatabaseError(
            f"Error checking if beacon index '{beacon_index}' is in table '{VALIDATORS_TABLE_KEY}'"
        ) from e


def update_beacon_constants(validators: list[dict[str, Any]]) -> None:
    """Saves the constant values from the beacon chain for the validators with the given pubkeys.
    These values should be updated only once. Thus:
        - If stake_signature exists, this deposit is unexpected; raise.
        - If proposal_signature exists, this deposit is the stake_deposit. Update:
            - VALIDATORS_STAKE_SIGNATURE_FIELD (str)
        - If not, update:
            - VALIDATORS_PROPOSAL_SLOT_FIELD (int)
            - VALIDATORS_BEACON_INDEX_FIELD (int)
            - VALIDATORS_WITHDRAWAL_CREDENTIALS_FIELD (str)
            - VALIDATORS_EXIT_EPOCH_FIELD (int)
            - VALIDATORS_PROPOSAL_SIGNATURE_FIELD (str)

    Args:
        validators (list[dict[str, BigInteger]]):
            List of dictionaries that can contain parsed validator data with keys:
            - VALIDATORS_PUBKEY_FIELD (str)
            - VALIDATORS_PROPOSAL_SLOT_FIELD (int, optional)
            - VALIDATORS_BEACON_INDEX_FIELD (int, optional)
            - VALIDATORS_WITHDRAWAL_CREDENTIALS_FIELD (str, optional)
            - VALIDATORS_EXIT_EPOCH_FIELD (int, optional)
            - VALIDATORS_PROPOSAL_SIGNATURE_FIELD (str, optional)
            - VALIDATORS_STAKE_SIGNATURE_FIELD (str, optional)

    Raises:
        DatabaseError: If there is an error updating beacon constants in the database.
        DatabaseMismatchError: An unexpected deposit is detected (stake_signature already exists).
    """
    try:
        with Database() as db:
            # Prepare lists to store the batches for executemany
            update_stake_signature_batch = []
            update_other_fields_batch = []

            for validator in validators:
                pubkey = validator.get(VALIDATORS_PUBKEY_FIELD)
                if not pubkey:
                    raise ValueError(f"Validator data missing '{VALIDATORS_PUBKEY_FIELD}'.")

                # Fetch the existing validator by pubkey
                db.execute(
                    SELECT_SIGNATURES_SQL,
                    {VALIDATORS_PUBKEY_FIELD: pubkey},
                )
                db_val = db.fetchone()
                if not db_val:
                    raise DatabaseMismatchError(f"Validator with pubkey '{pubkey}' does not exist.")

                proposal_signature, stake_signature = db_val

                # Check if stake_signature already exists
                if stake_signature:
                    send_email(
                        subject="An Alien is detected",
                        body=f"Unexpected deposit: stake_signature already exists for {pubkey}",
                    )
                    raise DatabaseMismatchError(
                        f"Unexpected deposit: stake_signature already exists for {pubkey}"
                    )

                # Add to the appropriate batch based on proposal_signature
                if proposal_signature:
                    # Add to batch for updating only stake_signature
                    if "stake_signature" not in validator:
                        raise ValueError(
                            f"Missing 'stake_signature' in validator data for {pubkey}."
                        )
                    update_stake_signature_batch.append(
                        {
                            VALIDATORS_STAKE_SIGNATURE_FIELD: validator[
                                VALIDATORS_STAKE_SIGNATURE_FIELD
                            ],
                            VALIDATORS_PUBKEY_FIELD: pubkey,
                        }
                    )
                else:
                    # Add to batch for updating other fields
                    required_fields = [
                        VALIDATORS_PROPOSAL_SLOT_FIELD,
                        VALIDATORS_BEACON_INDEX_FIELD,
                        VALIDATORS_WITHDRAWAL_CREDENTIALS_FIELD,  # as recorded on beacon chain
                        VALIDATORS_EXIT_EPOCH_FIELD,
                        VALIDATORS_PROPOSAL_SIGNATURE_FIELD,
                    ]

                    for field in required_fields:
                        if field not in validator:
                            raise ValueError(f"Missing '{field}' in validator data for {pubkey}")
                    update_other_fields_batch.append(
                        {
                            VALIDATORS_PROPOSAL_SIGNATURE_FIELD: validator[
                                VALIDATORS_PROPOSAL_SIGNATURE_FIELD
                            ],
                            VALIDATORS_PROPOSAL_SLOT_FIELD: validator[
                                VALIDATORS_PROPOSAL_SLOT_FIELD
                            ],
                            VALIDATORS_BEACON_INDEX_FIELD: validator[VALIDATORS_BEACON_INDEX_FIELD],
                            VALIDATORS_WITHDRAWAL_CREDENTIALS_FIELD: validator[
                                VALIDATORS_WITHDRAWAL_CREDENTIALS_FIELD
                            ],
                            VALIDATORS_EXIT_EPOCH_FIELD: validator[VALIDATORS_EXIT_EPOCH_FIELD],
                            VALIDATORS_PUBKEY_FIELD: pubkey,
                        }
                    )

            # Execute batch for updating stake_signature only for stake_deposit
            if update_stake_signature_batch:
                db.executemany(
                    UPDATE_STAKE_SIGNATURE_SQL,
                    update_stake_signature_batch,
                )

            # Execute batch for updating other fields for proposal deposit
            if update_other_fields_batch:
                db.executemany(
                    UPDATE_OTHER_FIELDS_SQL,
                    update_other_fields_batch,
                )

        get_logger().debug(f"Updated beaconchain related data for {len(validators)} validators")
    except Exception as e:
        raise DatabaseError(
            f"Error updating beaconchain related data on table {VALIDATORS_TABLE_KEY}"
        ) from e


def increase_withdrawn_balances(withdrawn_balances: dict[str, BigInteger]) -> None:
    """Increases the withdrawn_balance field for the given validators.

    Args:
        withdrawn_balances (dict[str, BigInteger]):
            A dictionary mapping validator beacon indices to the withdrawn amount to be processed:
            {'validator_index': amount,...}

    Raises:
        DatabaseError: If there is an error updating withdrawn balances in the database.
        DatabaseMismatchError: If a validator does not exist in the database.
    """
    try:
        with Database() as db:
            # Note that, we use TEXT on withdrawn_balance,
            # thus we can not simply do withdrawn_balance + :amount here.
            # So we will first fetch the current balances
            # and than increase before setting on db again

            validator_indices = list(withdrawn_balances.keys())
            if not validator_indices:
                get_logger().debug("No validators to update withdrawn balances for.")
                return

            # Generate the SELECT SQL with the correct number of placeholders
            select_sql = generate_select_fields_where_in_sql(
                table_key=VALIDATORS_TABLE_KEY,
                select_fields=[VALIDATORS_BEACON_INDEX_FIELD, VALIDATORS_WITHDRAWN_BALANCE_FIELD],
                condition_field=VALIDATORS_BEACON_INDEX_FIELD,
                num_values=len(validator_indices),
            )

            db.execute(
                select_sql,
                validator_indices,
            )
            balances = db.fetchall()

            if balances:
                updated_balances = []
                for db_val in balances:
                    validator_index, withdrawn_balance = db_val  # Assuming tuple order

                    new_balance = withdrawn_balances[validator_index] + int(withdrawn_balance)

                    updated_balances.append(
                        {
                            VALIDATORS_BEACON_INDEX_FIELD: validator_index,
                            VALIDATORS_WITHDRAWN_BALANCE_FIELD: str(new_balance),
                        }
                    )

                # Execute batch update for withdrawn_balance
                if updated_balances:
                    db.executemany(
                        UPDATE_WITHDRAWN_BALANCE_SQL,
                        updated_balances,
                    )

                get_logger().debug(
                    f"Updated withdrawn balances for {len(updated_balances)} validators"
                )
    except Exception as e:
        raise DatabaseError(
            f"Error updating withdrawn balances on table {VALIDATORS_TABLE_KEY}"
        ) from e


def increase_fee_recipient_balances(fee_recipient_balances: dict[str, BigInteger]) -> None:
    """Increases the fee_recipient_balance field for the given validators.

    Args:
        fee_recipient_balances (dict[str, BigInteger]):
            Mapping validator beacon indices to the fee recipient amount to be processed.

    Raises:
        DatabaseError: If there is an error updating fee recipient balances in the database.
        DatabaseMismatchError: If a validator does not exist in the database.
    """
    try:
        with Database() as db:
            validator_indices = list(fee_recipient_balances.keys())
            if not validator_indices:
                get_logger().debug("No validators to update fee recipient balances for.")
                return

            # Generate the SELECT SQL with the correct number of placeholders
            select_sql = generate_select_fields_where_in_sql(
                table_key=VALIDATORS_TABLE_KEY,
                select_fields=[
                    VALIDATORS_BEACON_INDEX_FIELD,
                    VALIDATORS_FEE_RECIPIENT_BALANCE_FIELD,
                ],
                condition_field=VALIDATORS_BEACON_INDEX_FIELD,
                num_values=len(validator_indices),
            )

            db.execute(
                select_sql,
                validator_indices,
            )
            balances = db.fetchall()

            updated_balances = []
            for db_val in balances:
                validator_index, fee_recipient_balance = db_val

                new_balance = fee_recipient_balances[validator_index] + int(fee_recipient_balance)

                updated_balances.append(
                    {
                        VALIDATORS_BEACON_INDEX_FIELD: validator_index,
                        VALIDATORS_FEE_RECIPIENT_BALANCE_FIELD: str(new_balance),
                    }
                )
                get_logger().info(f"{validator_index} gained {fee_recipient_balance}")

            # Execute batch update for fee_recipient_balance
            if updated_balances:
                db.executemany(
                    UPDATE_FEE_RECIPIENT_BALANCE_SQL,
                    updated_balances,
                )

            get_logger().debug(
                f"Updated fee recipient balances for {len(updated_balances)} validators"
            )
    except Exception as e:
        raise DatabaseError(
            f"Error updating fee recipient balances on table {VALIDATORS_TABLE_KEY}"
        ) from e
