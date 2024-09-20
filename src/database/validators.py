# -*- coding: utf-8 -*-

from src.classes import Database
from src.exceptions import DatabaseError, DatabaseMismatchError
from src.globals import get_logger
from src.helpers.portal import get_proposed_pubkeys, get_verification_index, get_validators_batch


def create_validators_table() -> None:
    """Creates the sql database table for Validators.

    Raises:
        DatabaseError: Error creating Validators table
    """

    try:
        with Database() as db:
            # TODO: not sure how to calculate the fee_recipient_balance
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
    except Exception as e:
        raise DatabaseError(f"Error dropping Validators table") from e


def reinitialize_validators_table() -> None:
    """Removes validators table and creates an empty one."""

    drop_validators_table()
    create_validators_table()


def insert_many_validators(new_validators: list[dict]) -> None:
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
    except Exception as e:
        raise DatabaseError(f"Error inserting many validators into table Validators") from e


def fill_validators_table(pks: list[str]) -> None:
    """Fills the validators table with the data of the given pubkeys.

    Args:
        pks (list[str]): pubkeys that will be fetched and inserted
    """
    insert_many_validators(get_validators_batch(pks))


def update_portal_validators(first_block, last_block) -> None:
    pks: list[str] = get_proposed_pubkeys(first_block, last_block)
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
                            "proposal_signature": validator["proposal_signature"],
                            "proposal_slot": validator["proposal_slot"],
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
                    SET stake_signature = :signature
                    WHERE pubkey = :pubkey
                    """,
                    update_stake_signature_batch,
                )

            # Execute batch for updating other fields for stake deposit
            if update_fields_batch:
                db.executemany(
                    """UPDATE Validators 
                    SET proposal_signature = :signature,
                        proposal_slot = :slot,
                        pubkey = :pubkey,
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
    """_summary_

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
                f"""SELECT validator_index, withdrawn_balance 
                FROM Validators 
                WHERE validator_index 
                IN ({placeholders})""",
                validator_indices,
            )
            balances = db.fetchall()

            updated_balances = []
            for validator_index, balance in balances:
                new_balance = int(withdrawn_balances[validator_index]) + int(balance)

                updated_balances.append(
                    {
                        "validator_index": validator_index,
                        "withdrawn_balance": str(new_balance),
                    }
                )

            db.executemany(
                """UPDATE Validators 
                    SET withdrawn_balance = :withdrawn_balance
                    WHERE validator_index = :validator_index
                """,
                updated_balances,
            )
        get_logger().debug(f"Updated withdrawn balances for {len(withdrawn_balances)} validators")

    except Exception as e:
        raise DatabaseError(f"Error updating withdrawn balances for on table Validators") from e


def check_pubkey(pubkey: str) -> bool:
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


def check_beacon_index(idx: int) -> bool:
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


def fetch_validator_balances() -> list[dict]:
    """Fetches the pubkey and validator balances (beacon and withdrawn) from the database.
    # TODO: fix this (later)
    Returns:
        list[dict]: List of validators pubkey, beacon_balance, withdrawn_balance
    """
    try:
        with Database() as db:
            db.execute("SELECT pubkey, beacon_balance, withdrawn_balance FROM Validators")
            return db.fetchall()
    except Exception as e:
        raise DatabaseError(f"Error fetching validators from table Validators") from e


def detect_proposed_validators(block_identifier: str) -> list[dict]:
    """Detects pending validators that are waiting to be approved by Oracle:
    proposal_signature exists, meaning the proposal deposit was processed.
    Has lower index than verification_index, meaning its portal_state is PENDING.

    Returns:
        list[dict]: List of validators with pubkey, portal_index, proposal_signature
    """
    v_idx: int = get_verification_index(block_identifier)
    try:
        with Database() as db:
            db.execute(
                """
                SELECT pubkey, portal_index, proposal_signature
                FROM Validators 
                WHERE proposal_signature IS NOT NULL,
                AND stake_signature IS NULL
                """,
                (v_idx,),
            )
            return db.fetchall()
    except Exception as e:
        raise DatabaseError(f"Error fetching validators from table Validators") from e
