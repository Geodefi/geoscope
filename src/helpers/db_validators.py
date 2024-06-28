# -*- coding: utf-8 -*-

from itertools import repeat
from geodefi.globals import VALIDATOR_STATE

from src.classes import Database
from src.globals import SDK
from src.logger import log
from src.utils import multithread
from src.exceptions import DatabaseError, DatabaseMismatchError
from .portal import get_StakeParams


def create_validators_table() -> None:
    """Creates the sql database table for Validators.

    Raises:
        DatabaseError: Error creating Validators table
    """

    try:
        with Database() as db:
            # fallback just records if operator is set as fallback.
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS Validators (
                    portal_index INTEGER NOT NULL UNIQUE,
                    beacon_index INTEGER NOT NULL UNIQUE,
                    pubkey TEXT NOT NULL PRIMARY KEY,
                    pool_id TEXT NOT NULL,
                    local_state INT NOT NULL,
                    portal_state INT NOT NULL,
                    signature31 INTEGER NOT NULL,
                    withdrawal_credentials TEXT NOT NULL,
                    exit_epoch INTEGER,
                    balance TEXT,
                    withdrawn_balance TEXT,
                    fee_recepient_balance TEXT
                )
                """
            )
        log.debug(f"Created a new table: Validators")
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


def fetch_validator(pubkey: str) -> dict:
    """Fetches the data for a validator with the given pubkey. Returns the gathered data.

    Args:
        pubkey (str): public key of the validator

    Returns:
        dict: dictionary containing the validator info
    """

    val = SDK.portal.validator(pubkey)

    return {
        "portal_index": val.portal_index,  # constant
        "beacon_index": val.beacon_index,  # constant
        "pubkey": val.pubkey,  # constant
        "pool_id": val.poolId,  # constant
        "local_state": val.portal_state,
        "portal_state": val.portal_state,
        "signature31": val.signature31,  # constant
        "withdrawal_credentials": val.withdrawal_credentials,  # constant
        "exit_epoch": val.exit_epoch,  # can be set after proposal tx is mined
    }


def fetch_validators_batch(pks: list[str]) -> list[dict]:
    """Fetches the data for validators within the given pks list. Returns the gathered data.

    Args:
        pks (list[str]): pubkeys that will be fetched

    Returns:
        list[dict]: list of dictionaries containing the validator info
    """

    return multithread(fetch_validator, pks)


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
                "INSERT INTO Validators VALUES (?,?,?,?,?,?,?,?,?)",
                [
                    (
                        a["portal_index"],
                        a["beacon_index"],
                        a["pubkey"],
                        a["pool_id"],
                        int(a["local_state"]),
                        int(a["portal_state"]),
                        a["signature31"],
                        a["withdrawal_credentials"],
                        a["exit_epoch"],
                    )
                    for a in new_validators
                ],
            )
    except Exception as e:
        raise DatabaseError(
            f"Error inserting many validators into table Validators"
        ) from e


def fill_validators_table(pks: list[str]) -> None:
    """Fills the validators table with the data of the given pubkeys.

    Args:
        pks (list[str]): pubkeys that will be fetched and inserted
    """
    insert_many_validators(fetch_validators_batch(pks))


def save_local_state(pubkey: str, local_state: VALIDATOR_STATE) -> None:
    """Sets local_state on db when it changes.

    Args:
        pubkey (str): public key of the validator
        local_state (VALIDATOR_STATE): new local state of the validator

    Raises:
        DatabaseError: Error updating local state of validator
    """

    try:
        with Database() as db:
            db.execute(
                """
                UPDATE Validators 
                SET local_storage = ?
                WHERE pubkey = ?
                """,
                (int(local_state), pubkey),
            )
        log.debug(f"Updated local_state to: {local_state}")
    except Exception as e:
        raise DatabaseError(
            f"Error updating local state of validator with pubkey {pubkey} \
                            and state {local_state} to table Validators"
        ) from e


def save_portal_state(pubkey: str, portal_state: VALIDATOR_STATE) -> None:
    """Sets portal_state on db when it changes on chain.

    Args:
        pubkey (str): public key of the validator
        portal_state (VALIDATOR_STATE): new portal state of the validator

    Raises:
        DatabaseError: Error updating portal state of validator
    """

    try:
        with Database() as db:
            db.execute(
                """
                UPDATE Validators 
                SET portal_state = ?
                WHERE pubkey = ?
                """,
                (int(portal_state), pubkey),
            )
            log.debug(f"Updated portal_state to: {portal_state}")
    except Exception as e:
        raise DatabaseError(
            f"Error updating portal state of validator with pubkey {pubkey} \
                            and state {portal_state} to table Validators"
        ) from e


def save_exit_epoch(pubkey: str, exit_epoch: str) -> None:
    """Sets exit_epoch on db when it changes on chain.

    Args:
        pubkey (str): public key of the validator
        exit_epoch (str): new exit epoch of the validator

    Raises:
        DatabaseError: Error updating exit epoch of validator
    """
    # did not we
    try:
        log.debug(f"Updated the exit epoch: {exit_epoch}")
        with Database() as db:
            db.execute(
                """
                UPDATE Validators 
                SET exit_epoch = ?
                WHERE pubkey = ?
                """,
                (int(exit_epoch), pubkey),
            )
    except Exception as e:
        raise DatabaseError(
            f"Error updating exit epoch of validator with pubkey {pubkey} \
                            and epoch {exit_epoch} to table Validators"
        ) from e


def save_beacon_balances(pubkeys: list[str], balances: list[str]) -> None:
    """Saves the beacon balances of the validators with the given pubkeys.

    Args:
        pubkeys (list[str]): public keys of the validators
        balances (list[str]): balances of the validators

    Raises:
        DatabaseError: Error updating beacon balances of validators
    """

    try:
        with Database() as db:
            db.executemany(
                "UPDATE Validators SET beacon_balance = ? WHERE pubkey = ?",
                zip(balances, pubkeys),
            )
        log.debug(f"Updated beacon balances of {len(pubkeys)} validators")
    except Exception as e:
        raise DatabaseError(
            f"Error updating beacon balances of validators {pubkeys} to table Validators"
        ) from e


def fetch_verified_pks() -> list[str]:
    """Fetches the data of the validators that are in the proposed state.

    Returns:
        list[str]: list of public keys of validators in proposed state

    Raises:
        DatabaseError: Error fetching validators from table
    """
    verification_index: int = get_StakeParams()[4]

    try:
        with Database() as db:
            db.execute(
                """
                SELECT pubkey FROM Validators 
                WHERE local_state = ?  
                AND portal_index < ?
                ORDER BY pool_id
                """,
                (int(VALIDATOR_STATE.PROPOSED), verification_index),
            )
            approved_pks: list[str] = db.fetchall()
            log.info(
                f"{len(approved_pks)} new verified public keys are detected."
            )
            log.debug(",".join(map(str, approved_pks)))

            return approved_pks
    except Exception as e:
        raise DatabaseError(
            f"Error fetching validators from table Validators"
        ) from e


def check_pk_in_db(pubkey: str) -> bool:
    """Checks if the given public key is in the database.

    Args:
        pubkey (str): public key of the validator

    Returns:
        bool: True if the public key is in the database, False otherwise

    Raises:
        DatabaseError: Error checking if pubkey is in table Validators
    """
    try:
        with Database() as db:
            db.execute("SELECT * FROM Validators WHERE pubkey = ?", (pubkey,))
            return db.fetchone() is not None
    except Exception as e:
        raise DatabaseError(
            f"Error checking if pubkey {pubkey} is in table Validators"
        ) from e


def fetch_pool_id(pubkey: str) -> str:
    """Fetches the pool_id of the validator with the given pubkey.

    Args:
        pubkey (str): public key of the validator

    Returns:
        int: pool_id of the validator
    """

    try:
        with Database() as db:
            db.execute(
                "SELECT pool_id FROM Validators WHERE pubkey = ?", (pubkey,)
            )
            return db.fetchone()[0]
    except Exception as e:
        raise DatabaseMismatchError(
            f"Validator pubkey {pubkey} not found in the database"
        ) from e


# TODO: write functions to fetch beacon_balance, withdrawn_balance and fee_recepient_balance grouped by pool_id
#       like returns a list of dicts


def fetch_balances_by_pool_id(pool_id: str, validator_states: list) -> dict:
    """Fetches the balances of the validators with the given pool_id.

    Args:
        pool_id (str): pool_id of the validators
        validator_states (list): list of states that the validators should have

    Returns:
        dict: dictionary containing the balances of the validators
    """

    try:
        with Database() as db:
            db.execute(
                f"""
                SELECT beacon_balance, withdrawn_balance, fee_recepient_balance
                FROM Validators
                WHERE pool_id = ?
                AND beacon_state IN ({"?" * len(validator_states)})
                """,
                [pool_id] + validator_states,
            )
            return db.fetchall()
    except Exception as e:
        raise DatabaseMismatchError(
            f"Error fetching balances of validators with pool_id {pool_id}"
        ) from e


def fetch_balances_by_pool_id_batch(
    pool_ids: list[str], validator_states: list
) -> dict:
    """Fetches the balances of the validators with the given pool_ids.

    Args:
        pool_ids (list[str]): pool_ids of the validators
        validator_states (list): list of states that the validators should have

    Returns:
        dict: dictionary containing the balances of the validators
    """

    return multithread(
        fetch_balances_by_pool_id, pool_ids, repeat(validator_states)
    )
