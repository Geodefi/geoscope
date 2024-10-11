# -*- coding: utf-8 -*-

from src.classes import Database
from src.exceptions import DatabaseError, DatabaseMismatchError
from src.globals import get_logger
from src.helpers.portal import (
    fetch_proposed_pubkeys,
    fetch_verification_index,
    fetch_portal_validators_batch,
)


def create_validators_table() -> None:
    """Creates the sql database table for Validators.

    Raises:
        DatabaseError: Error creating Validators table
    """

    try:
        with Database() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS Validators (
                    pubkey TEXT NOT NULL PRIMARY KEY,
                    portal_index INTEGER NOT NULL UNIQUE,
                    pool_id TEXT NOT NULL,
                    operator_id TEXT NOT NULL,
                    pool_fee TEXT NOT NULL,
                    operator_fee TEXT NOT NULL,
                    infrastructure_fee TEXT NOT NULL,
                    signature31 TEXT NOT NULL,
                    beacon_index INTEGER UNIQUE,
                    withdrawal_credentials TEXT,
                    exit_epoch TEXT,
                    stake_signature TEXT,
                    proposal_signature TEXT,
                    proposal_slot INT,
                    withdrawn_balance TEXT,
                    last_withdrawn TEXT
                    fee_recipient_balance TEXT 
                )
                """
            )
        get_logger().debug(f"Created a new table: Validators")
    except Exception as e:
        raise DatabaseError(f"Error creating Validators table") from e


def drop_validators_table() -> None:
    """Removes Validators table from the database.

    Raises:
        DatabaseError: Error dropping Validators table
    """

    try:
        with Database() as db:
            db.execute("""DROP TABLE IF EXISTS Validators""")
        get_logger().debug(f"Dropped Table: Validators")
    except Exception as e:
        raise DatabaseError(f"Error dropping Validators table") from e


def reinitialize_validators_table() -> None:
    """Removes validators table and creates an empty one."""

    drop_validators_table()
    create_validators_table()


def insert_validators_batch(new_validators: list[dict]) -> None:
    """Inserts the given validators data into the database.

    Args:
        new_validators (list[dict]): list of dictionaries containing the validator info

    Raises:
        DatabaseError: Error inserting many validators into table
    """

    try:
        with Database() as db:
            db.executemany(
                """
                INSERT INTO Validators VALUES (
                    :pubkey,
                    :portal_index,
                    :pool_id,
                    :operator_id,
                    :pool_fee,
                    :operator_fee,
                    :infrastructure_fee,
                    :signature31,
                    :beacon_index,
                    :withdrawal_credentials,
                    :exit_epoch,
                    :stake_signature,
                    :proposal_signature,
                    :proposal_slot,
                    :withdrawn_balance,
                    :fee_recipient_balance
                )
                """,
                new_validators,
            )
        get_logger().debug(f"Inserted {len(new_validators)} new validators in Validators table")
    except Exception as e:
        raise DatabaseError(f"Error inserting many validators into table Validators") from e


def fill_validators_table(pks: list[str]) -> None:
    """Fills the validators table with the data of the given pubkeys.

    Args:
        pks (list[str]): pubkeys that will be fetched and inserted
    """
    insert_validators_batch(fetch_portal_validators_batch(pks))


def update_portal_validators(first_block, last_block) -> None:
    pks: list[str] = fetch_proposed_pubkeys(first_block, last_block)
    fill_validators_table(pks)


def update_beacon_constants(validators: list[dict]) -> None:
    """Saves the constant values from the beacon chain for the validators with the given pubkeys.
    These values should be updated only once. Thus,
    if stake_signature exists, this deposit is unexpected, raise.
    if proposal_signature exists, this deposit is the stake_deposit. Update:
        - stake_signature
    if not:
        - proposal_signature
        - proposal_slot
        - pubkey
        - beacon_index
        - withdrawal_credentials
        - exit_epoch
    will be updated.

    Args:
        validators (list[dict]): list of dicts of parsed validator data.


    Raises:
        DatabaseError: Error updating beacon balances of validators
    """
    try:
        with Database() as db:
            # Prepare lists to store the batches for executemany
            update_stake_signature_batch = []
            update_fields_batch = []

            for validator in validators:
                pubkey = validator["pubkey"]

                # Fetch the existing validator by pubkey
                db_val = db.execute(
                    """SELECT proposal_signature, stake_signature
                    FROM Validators 
                    WHERE pubkey = :pubkey
                    """,
                    {"pubkey": pubkey},
                ).fetchone()

                # Check if stake_signature already exists
                if db_val["stake_signature"]:
                    # TODO: send mail here
                    raise DatabaseMismatchError(
                        f"Unexpected deposit: stake_signature already exists for pubkey {pubkey}"
                    )

                # Add to the appropriate batch based on proposal_signature
                if db_val["proposal_signature"]:
                    # Add to batch for updating only stake_signature
                    update_stake_signature_batch.append(
                        {"stake_signature": validator["stake_signature"], "pubkey": pubkey}
                    )
                else:
                    # Add to batch for updating other fields
                    update_fields_batch.append(
                        {
                            "signature": validator["proposal_signature"],
                            "slot": validator["proposal_slot"],
                            "pubkey": validator["pubkey"],
                            "beacon_index": validator["beacon_index"],
                            "withdrawal_credentials": validator["withdrawal_credentials"],
                            "exit_epoch": validator["exit_epoch"],
                        }
                    )

            # Execute batch for updating stake_signature only for proposal deposit
            if update_stake_signature_batch:
                db.executemany(
                    """UPDATE Validators 
                    SET stake_signature = :stake_signature
                    WHERE pubkey = :pubkey
                    """,
                    update_stake_signature_batch,
                )

            # Execute batch for updating other fields for stake deposit
            if update_fields_batch:
                db.executemany(
                    """UPDATE Validators 
                    SET proposal_signature = :proposal_signature,
                        proposal_slot = :proposal_slot,
                        beacon_index = :beacon_index,
                        withdrawal_credentials = :withdrawal_credentials,
                        exit_epoch = :exit_epoch
                    WHERE pubkey = :pubkey
                    """,
                    update_fields_batch,
                )

        get_logger().debug(f"Updated beaconchain related data for {len(validators)} validators")
    except Exception as e:
        raise DatabaseError(f"Error updating beaconchain related data on table Validators") from e


def increase_withdrawn_balances(withdrawn_balances: dict):
    """Increases the withdrawn_balance field for the given validators.


    Args:
        withdrawn_balances (dict): {validator_index: amount},\
            validator indices mapped to withdrawn amount to be processed. 

    Raises:
        DatabaseError: Error updating beacon balances of validators
    """

    try:
        with Database() as db:
            # Note that, we use TEXT on withdrawn_balance,
            # thus we can not simply do withdrawn_balance + :amount here.
            # So we will first fetch the current balances
            # and than increase before setting on db again

            validator_indices = withdrawn_balances.keys()
            placeholders = ",".join("?" * len(validator_indices))
            db.execute(
                f"""SELECT beacon_index, withdrawn_balance 
                FROM Validators 
                WHERE beacon_index 
                IN ({placeholders})""",
                validator_indices,
            )
            balances = db.fetchall()

            updated_balances = []
            for validator_index, withdrawn_balance in balances:
                new_balance = int(withdrawn_balances[validator_index]) + int(withdrawn_balance)

                updated_balances.append(
                    {
                        "validator_index": validator_index,
                        "withdrawn_balance": str(new_balance),
                    }
                )

            db.executemany(
                """UPDATE Validators 
                    SET withdrawn_balance = :withdrawn_balance
                    WHERE beacon_index = :validator_index
                """,
                updated_balances,
            )
        get_logger().debug(f"Updated withdrawn balances for {len(withdrawn_balances)} validators")

    except Exception as e:
        raise DatabaseError(f"Error updating withdrawn balances for on table Validators") from e


def increase_fee_recipient_balances(fee_recipient_balances: dict):
    """Increases the fee_recipient_balance field for the given validators.

    Args:
        fee_recipient_balances (dict): {validator_index: amount},
            validator indices mapped to fee recipient amount to be processed.

    Raises:
        DatabaseError: Error updating fee recipient balances of validators.
    """

    try:
        with Database() as db:
            # Fetch the current fee_recipient_balance from the Validators table
            validator_indices = fee_recipient_balances.keys()
            placeholders = ",".join("?" * len(validator_indices))
            db.execute(
                f"""SELECT beacon_index, fee_recipient_balance 
                FROM Validators 
                WHERE beacon_index 
                IN ({placeholders})""",
                validator_indices,
            )
            balances = db.fetchall()

            updated_balances = []
            for validator_index, fee_recipient_balance in balances:
                # Sum the new fee_recipient_balance with the existing one
                new_balance = int(fee_recipient_balances[validator_index]) + int(
                    fee_recipient_balance
                )

                updated_balances.append(
                    {
                        "validator_index": validator_index,
                        "fee_recipient_balance": str(new_balance),
                    }
                )

            # Update the Validators table with the new fee_recipient_balance
            db.executemany(
                """UPDATE Validators 
                    SET fee_recipient_balance = :fee_recipient_balance
                    WHERE beacon_index = :validator_index
                """,
                updated_balances,
            )

        get_logger().debug(
            f"Updated fee recipient balances for {len(fee_recipient_balances)} validators"
        )

    except Exception as e:
        raise DatabaseError(f"Error updating fee recipient balances in table Validators") from e


def check_validator_by_pubkey(pubkey: str) -> bool:
    """Checks if a given pubkey is saved in the Database.
        Determining if a pubkey is created through the Portal until the latest processed slot.

    Args:
        pubkey (str): public key of the validator

    Returns:
        bool: True if the public key is in the database, False otherwise

    Raises:
        DatabaseMismatchError: There are more than 1 validators with the same pubkey.
        DatabaseError: Error checking if pubkey is in table Validators
    """
    try:
        with Database() as db:
            db.execute("SELECT * FROM Validators WHERE pubkey = ?", (pubkey,))
            result = db.fetchall()
            if result:
                if len(result) == 1:
                    return True
                else:
                    raise DatabaseMismatchError(
                        f"There are {len(result)} validators \
                            with the same pubkey in table Validators"
                    )
            return False
    except Exception as e:
        raise DatabaseError(f"Error checking if pubkey {pubkey} is in table Validators") from e


def check_validator_by_beacon_index(idx: int) -> bool:
    """Checks if a given beacon chain index is saved in the Database.
        Determining if a pubkey is created through the Portal until the latest processed slot.

    Args:
        pubkey (str): public key of the validator

    Returns:
        bool: True if the public key is in the database, False otherwise

    Raises:
        DatabaseMismatchError: There are more than 1 validators with the same beacon_index.
        DatabaseError: Error checking if pubkey is in table Validators
    """
    try:
        with Database() as db:
            db.execute("SELECT * FROM Validators WHERE beacon_index = ?", (idx,))
            result = db.fetchall()
            if result:
                if len(result) == 1:
                    return True
                else:
                    raise DatabaseMismatchError(
                        f"There are {len(result)} validators with \
                            the same beacon_index in table Validators"
                    )
            return False
    except Exception as e:
        raise DatabaseError(f"Error checking if index {idx} is in table Validators") from e


def read_validator_balances() -> list[tuple]:
    """Fetches the pubkey and validator balances (beacon and withdrawn) from the database.
    Returns:
        list[dict]: List of pubkey, withdrawn_balance, fee_recipient_balance
    """
    # TODO: this function is not proper, it might be better to change according to Crash's implementation, later.
    try:
        with Database() as db:
            db.execute("SELECT pubkey, withdrawn_balance, fee_recipient_balance FROM Validators")
            return db.fetchall()
    except Exception as e:
        raise DatabaseError(f"Error fetching validators from table Validators") from e


def read_proposed_validators(block_identifier: str) -> list[tuple]:
    """Detects pending validators that are waiting to be approved by Oracle:
        - Proposal_signature exists, meaning the proposal deposit was processed.
        - Has lower index than verification_index, meaning its portal_state is PENDING.

    Returns:
        list[dict]: List of validators with pubkey, portal_index pool_id signature31 withdrawal_credentials, proposal_signature, stake_signature proposal_slot
    """
    v_idx: int = fetch_verification_index(block_identifier)
    try:
        with Database() as db:
            db.execute(
                """
                SELECT 
                    pubkey, 
                    portal_index,
                    pool_id,
                    signature31,
                    withdrawal_credentials, 
                    proposal_signature, 
                    stake_signature,
                    proposal_slot
                FROM Validators 
                WHERE proposal_signature IS NOT NULL,
                AND portal_index > :verification_index
                """,
                {"verification_index": v_idx},
            )
            return db.fetchall()
    except Exception as e:
        raise DatabaseError(f"Error fetching validators from table Validators") from e


def read_validators_by_pool(pool_id: str) -> list[tuple]:
    """Fetches the pubkeys, pool_fees, operator_fees, infrastructure_fees,
        withdrawn_balance, last_withdrawns and fee_recipient_balance of the validators in the given pool.

    Args:
        pool_id (str): The pool id to fetch the validators for.

    Returns:
        list[tuple]: List of tuples containing the validators data.
    """
    try:
        with Database() as db:
            db.execute(
                """
                SELECT pubkey, pool_fee, operator_fee, infrastructure_fee, withdrawn_balance, last_withdrawn, fee_recipient_balance
                FROM Validators
                WHERE pool_id = :pool_id
                """,
                {"pool_id": pool_id},
            )
            return db.fetchall()
    except Exception as e:
        raise DatabaseError(
            f"Error fetching validators from pool {pool_id} from table Validators"
        ) from e


def read_operator_id_by_beacon_index(beacon_index) -> int:
    try:
        with Database() as db:
            db.execute(
                """
                    SELECT operator_id
                    FROM Validators
                    WHERE beacon_index = :beacon_index
                    """,
                {"beacon_index": beacon_index},
            )
            return db.fetchall()
    except Exception as e:
        raise DatabaseError(
            f"Error fetching operator_id with index {beacon_index} from table Validators"
        ) from e
