import os
from typing import Any, Callable

import click

from src.common import StringListParamType
from src.exceptions import MissingConfigurationError
from src.globals.constants.config import (
    CHAIN_CONSENSUS_API_FIELD,
    CHAIN_EXECUTION_API_FIELD,
    CHAIN_IDENTIFIER_FIELD,
    CHAIN_INTERVAL_FIELD,
    CHAIN_RANGE_SLOT_FIELD,
    CHAIN_SECTION_KEY,
    CHAIN_START_SLOT_FIELD,
    DB_BACKUP_DIR_FIELD,
    DB_BACKUP_INTERVAL_FIELD,
    DB_BACKUP_KEEP_FIELD,
    DB_BACKUP_SECTION_KEY,
    DB_DIR_FIELD,
    DB_SECTION_KEY,
    DEFAULT_CHAIN_IDENTIFIER,
    DEFAULT_CHAIN_INTERVAL,
    DEFAULT_CHAIN_RANGE_SLOT,
    DEFAULT_DB_BACKUP_DIR,
    DEFAULT_DB_BACKUP_INTERVAL,
    DEFAULT_DB_BACKUP_KEEP,
    DEFAULT_DB_DIR,
    DEFAULT_EMAIL_SMTP_PORT,
    DEFAULT_EMAIL_SMTP_SERVER,
    DEFAULT_GAS_PARSER_BASE,
    DEFAULT_GAS_PARSER_PRIORITY,
    DEFAULT_LOGGER_BACKUP_KEEP,
    DEFAULT_LOGGER_BACKUP_WHEN,
    DEFAULT_LOGGER_DIR,
    DEFAULT_LOGGER_FORMAT_DATE,
    DEFAULT_LOGGER_FORMAT_MESSAGE,
    DEFAULT_LOGGER_LEVEL,
    DEFAULT_NETWORK_ATTEMPT_RATE,
    DEFAULT_NETWORK_MAX_ATTEMPT,
    DEFAULT_NETWORK_REFRESH_RATE,
    DEFAULT_STRATEGY_MAX_PENDING_VALIDATORS,
    DEFAULT_STRATEGY_MAX_VERIFICATION_DELAY,
    DEFAULT_STRATEGY_MERKLE_REFRESH_RATE,
    DEFAULT_STRATEGY_MIN_VERIFICATION_DELAY,
    DEFAULT_STRATEGY_PRICE_CHANGE_THRESHOLD,
    DEFAULT_STRATEGY_SLOT_PERIOD,
    EMAIL_RECEIVERS_FIELD,
    EMAIL_SECTION_KEY,
    EMAIL_SENDER_FIELD,
    EMAIL_SMTP_PORT_FIELD,
    EMAIL_SMTP_SERVER_FIELD,
    GAS_API_FIELD,
    GAS_MAX_BASE_FIELD,
    GAS_MAX_PRIORITY_FIELD,
    GAS_PARSER_BASE_FIELD,
    GAS_PARSER_PRIORITY_FIELD,
    GAS_PARSER_SECTION_KEY,
    GAS_SECTION_KEY,
    LOGGER_BACKUP_KEEP_FIELD,
    LOGGER_BACKUP_SECTION_KEY,
    LOGGER_BACKUP_WHEN_FIELD,
    LOGGER_DIR_FIELD,
    LOGGER_FORMAT_DATE_FIELD,
    LOGGER_FORMAT_MESSAGE_FIELD,
    LOGGER_FORMAT_SECTION_KEY,
    LOGGER_LEVEL_FIELD,
    LOGGER_SECTION_KEY,
    MAX_DB_BACKUP_KEEP,
    MAX_GAS_BASE_FEE,
    MAX_GAS_PRIORITY_FEE,
    MAX_NETWORK_ATTEMPT_RATE,
    MAX_NETWORK_MAX_ATTEMPT,
    MAX_NETWORK_REFRESH_RATE,
    MAX_STRATEGY_MAX_PENDING_VALIDATORS,
    MAX_STRATEGY_MAX_VERIFICATION_DELAY,
    MAX_STRATEGY_MERKLE_REFRESH_RATE,
    MAX_STRATEGY_MIN_VERIFICATION_DELAY,
    MAX_STRATEGY_PRICE_CHANGE_THRESHOLD,
    MAX_STRATEGY_SLOT_PERIOD,
    MIN_NETWORK_ATTEMPT_RATE,
    MIN_RANGE_VALUE,
    NETWORK_ATTEMPT_RATE_FEILD,
    NETWORK_MAX_ATTEMPT_FEILD,
    NETWORK_REFRESH_RATE_FIELD,
    NETWORK_SECTION_KEY,
    SCHEMA_DEFAULT_KEY,
    SCHEMA_HELP_KEY,
    SCHEMA_MUTATOR_KEY,
    SCHEMA_TYPE_KEY,
    STRATEGY_MAX_PENDING_VALIDATORS_FIELD,
    STRATEGY_MAX_VERIFICATION_DELAY_FIELD,
    STRATEGY_MERKLE_REFRESH_RATE_FIELD,
    STRATEGY_MIN_VERIFICATION_DELAY_FIELD,
    STRATEGY_PRICE_CHANGE_THRESHOLD_FIELD,
    STRATEGY_SECTION_KEY,
    STRATEGY_SLOT_PERIOD_FIELD,
    WATCHERS_FIELD,
)


def __replace_with_env_factory(env_var: str) -> Callable:
    placeholder = "<" + env_var + ">"

    def replace_with_env(value: str) -> str:
        if placeholder in value:
            env_value = os.getenv(env_var, None)
            if env_value is None:
                raise MissingConfigurationError(
                    f"{env_var} environment variable was expected, but not provided."
                )
            value = value.replace(placeholder, env_value)
        return value

    return replace_with_env


CONFIG_SCHEMA: dict[str, Any] = {
    CHAIN_SECTION_KEY: {
        CHAIN_START_SLOT_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.IntRange(min=MIN_RANGE_VALUE),
            SCHEMA_HELP_KEY: "The first slot to be considered while indexing the execution layer "
            "of the given chain.",
        },
        CHAIN_RANGE_SLOT_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.IntRange(min=MIN_RANGE_VALUE),
            SCHEMA_HELP_KEY: "The range for the event filters while fetching on chain data.",
            SCHEMA_DEFAULT_KEY: DEFAULT_CHAIN_RANGE_SLOT,
        },
        CHAIN_IDENTIFIER_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.Choice(["head", "finalized"]),
            SCHEMA_HELP_KEY: "Identifier while fetching new blocks.",
            SCHEMA_DEFAULT_KEY: DEFAULT_CHAIN_IDENTIFIER,
        },
        CHAIN_INTERVAL_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.IntRange(min=MIN_RANGE_VALUE),
            SCHEMA_HELP_KEY: "Average block time to rely on for given chain.",
            SCHEMA_DEFAULT_KEY: DEFAULT_CHAIN_INTERVAL,
        },
        CHAIN_EXECUTION_API_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.STRING,
            SCHEMA_HELP_KEY: "Api endpoint for the execution layer."
            " Could be the rest api of the execution client."
            " Can include <API_KEY_EXECUTION> which will be overriden.",
            SCHEMA_MUTATOR_KEY: __replace_with_env_factory(env_var="API_KEY_EXECUTION"),
        },
        CHAIN_CONSENSUS_API_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.STRING,
            SCHEMA_HELP_KEY: "Api endpoint for the consensus layer."
            " Could be the rest api of the consensus client."
            " Can include <API_KEY_CONSENSUS> which will be overriden.",
            SCHEMA_MUTATOR_KEY: __replace_with_env_factory(env_var="API_KEY_CONSENSUS"),
        },
    },
    STRATEGY_SECTION_KEY: {
        STRATEGY_SLOT_PERIOD_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.IntRange(MIN_RANGE_VALUE, MAX_STRATEGY_SLOT_PERIOD),
            SCHEMA_HELP_KEY: "(slots) The interval for the beacon chain indexer."
            " Number of slots between two Daemon runs.",
            SCHEMA_DEFAULT_KEY: DEFAULT_STRATEGY_SLOT_PERIOD,
        },
        STRATEGY_MIN_VERIFICATION_DELAY_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.IntRange(MIN_RANGE_VALUE, MAX_STRATEGY_MIN_VERIFICATION_DELAY),
            SCHEMA_HELP_KEY: "(seconds) Minimum delay for a validator ",
            SCHEMA_DEFAULT_KEY: DEFAULT_STRATEGY_MIN_VERIFICATION_DELAY,
        },
        STRATEGY_MAX_VERIFICATION_DELAY_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.IntRange(MIN_RANGE_VALUE, MAX_STRATEGY_MAX_VERIFICATION_DELAY),
            SCHEMA_HELP_KEY: "(seconds) Minimum delay between 2 updateVerificationIndex calls.",
            SCHEMA_DEFAULT_KEY: DEFAULT_STRATEGY_MAX_VERIFICATION_DELAY,
        },
        STRATEGY_MAX_PENDING_VALIDATORS_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.IntRange(MIN_RANGE_VALUE, MAX_STRATEGY_MAX_PENDING_VALIDATORS),
            SCHEMA_HELP_KEY: "Maximum number of validators to buffer before"
            " calling updateVerificationIndex",
            SCHEMA_DEFAULT_KEY: DEFAULT_STRATEGY_MAX_PENDING_VALIDATORS,
        },
        STRATEGY_PRICE_CHANGE_THRESHOLD_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.FloatRange(MIN_RANGE_VALUE, MAX_STRATEGY_PRICE_CHANGE_THRESHOLD),
            SCHEMA_HELP_KEY: "Minimum price change to trigger a merkle root update,"
            " overrides by merkle-refresh-rate",
            SCHEMA_DEFAULT_KEY: DEFAULT_STRATEGY_PRICE_CHANGE_THRESHOLD,
        },
        STRATEGY_MERKLE_REFRESH_RATE_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.IntRange(MIN_RANGE_VALUE, MAX_STRATEGY_MERKLE_REFRESH_RATE),
            SCHEMA_HELP_KEY: "Maximum interval between regular merkle root updates,"
            " overriden by price-change-threshold",
            SCHEMA_DEFAULT_KEY: DEFAULT_STRATEGY_MERKLE_REFRESH_RATE,
        },
    },
    NETWORK_SECTION_KEY: {
        NETWORK_REFRESH_RATE_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.IntRange(MIN_RANGE_VALUE, MAX_NETWORK_REFRESH_RATE),
            SCHEMA_HELP_KEY: "Cached data will be refreshed after provided delay (s).",
            SCHEMA_DEFAULT_KEY: DEFAULT_NETWORK_REFRESH_RATE,
        },
        NETWORK_MAX_ATTEMPT_FEILD[-1]: {
            SCHEMA_TYPE_KEY: click.IntRange(MIN_RANGE_VALUE, MAX_NETWORK_MAX_ATTEMPT),
            SCHEMA_HELP_KEY: "Api requests will fail after these many call attempts.",
            SCHEMA_DEFAULT_KEY: DEFAULT_NETWORK_MAX_ATTEMPT,
        },
        NETWORK_ATTEMPT_RATE_FEILD[-1]: {
            SCHEMA_TYPE_KEY: click.FloatRange(MIN_NETWORK_ATTEMPT_RATE, MAX_NETWORK_ATTEMPT_RATE),
            SCHEMA_HELP_KEY: "Interval between api requests (s).",
            SCHEMA_DEFAULT_KEY: DEFAULT_NETWORK_ATTEMPT_RATE,
        },
    },
    LOGGER_SECTION_KEY: {
        LOGGER_DIR_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.STRING,
            SCHEMA_HELP_KEY: "Directory name that log files will be stored.",
            SCHEMA_DEFAULT_KEY: DEFAULT_LOGGER_DIR,
        },
        LOGGER_LEVEL_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
            SCHEMA_HELP_KEY: "Set logging level for both stream and log file.",
            SCHEMA_DEFAULT_KEY: DEFAULT_LOGGER_LEVEL,
        },
        LOGGER_FORMAT_SECTION_KEY: {
            LOGGER_FORMAT_MESSAGE_FIELD[-1]: {
                SCHEMA_TYPE_KEY: click.STRING,
                SCHEMA_HELP_KEY: "Message format for the logger.",
                SCHEMA_DEFAULT_KEY: DEFAULT_LOGGER_FORMAT_MESSAGE,
            },
            LOGGER_FORMAT_DATE_FIELD[-1]: {
                SCHEMA_TYPE_KEY: click.STRING,
                SCHEMA_HELP_KEY: "Date format for the logger messages.",
                SCHEMA_DEFAULT_KEY: DEFAULT_LOGGER_FORMAT_DATE,
            },
        },
        LOGGER_BACKUP_SECTION_KEY: {
            LOGGER_BACKUP_WHEN_FIELD[-1]: {
                SCHEMA_TYPE_KEY: click.Choice(
                    ["S", "M", "H", "D", "W0", "W1", "W2", "W3", "W4", "W5", "W6", "midnight"],
                ),
                SCHEMA_HELP_KEY: "When should logger backup the current file"
                " and continue with a new file.",
                SCHEMA_DEFAULT_KEY: DEFAULT_LOGGER_BACKUP_WHEN,
            },
            LOGGER_BACKUP_KEEP_FIELD[-1]: {
                SCHEMA_TYPE_KEY: click.INT,
                SCHEMA_HELP_KEY: "The number of maximum logger files that will be kept."
                " Oldest ones will be peridocally deleted.",
                SCHEMA_DEFAULT_KEY: DEFAULT_LOGGER_BACKUP_KEEP,
            },
        },
    },
    DB_SECTION_KEY: {
        DB_DIR_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.STRING,
            SCHEMA_HELP_KEY: "Directory name for database folder, within --main-dir .",
            SCHEMA_DEFAULT_KEY: DEFAULT_DB_DIR,
        },
        DB_BACKUP_SECTION_KEY: {
            DB_BACKUP_DIR_FIELD[-1]: {
                SCHEMA_TYPE_KEY: click.STRING,
                SCHEMA_HELP_KEY: "Absolute path for the database backups",
                SCHEMA_DEFAULT_KEY: DEFAULT_DB_BACKUP_DIR,
            },
            DB_BACKUP_INTERVAL_FIELD[-1]: {
                SCHEMA_TYPE_KEY: click.IntRange(min=3600),
                SCHEMA_HELP_KEY: "(seconds) Interval between 2 automatic database backups."
                " If there are no old backups",
                SCHEMA_DEFAULT_KEY: DEFAULT_DB_BACKUP_INTERVAL,
            },
            DB_BACKUP_KEEP_FIELD[-1]: {
                SCHEMA_TYPE_KEY: click.IntRange(max=MAX_DB_BACKUP_KEEP),
                SCHEMA_HELP_KEY: "How many backups to keep in storage. Oldest ones are deleted.",
                SCHEMA_DEFAULT_KEY: DEFAULT_DB_BACKUP_KEEP,
            },
        },
    },
    GAS_SECTION_KEY: {
        GAS_MAX_PRIORITY_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.IntRange(MIN_RANGE_VALUE, MAX_GAS_PRIORITY_FEE),
            SCHEMA_HELP_KEY: "(gwei) Maximum priority fee while creating"
            " and submitting transactions",
        },
        GAS_MAX_BASE_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.IntRange(MIN_RANGE_VALUE, MAX_GAS_BASE_FEE),
            SCHEMA_HELP_KEY: "(gwei) Maximum base fee while creating and submitting transactions",
        },
        GAS_API_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.STRING,
            SCHEMA_HELP_KEY: "Api endpoint used for fetching gas prices (in gwei)."
            " Can include <API_KEY_GAS> which will be overriden.",
            SCHEMA_MUTATOR_KEY: __replace_with_env_factory(env_var="API_KEY_GAS"),
        },
        GAS_PARSER_SECTION_KEY: {
            GAS_PARSER_PRIORITY_FIELD[-1]: {
                SCHEMA_TYPE_KEY: click.STRING,
                SCHEMA_HELP_KEY: "String that describes how to parse the gas-api for priority fee.",
                SCHEMA_DEFAULT_KEY: DEFAULT_GAS_PARSER_PRIORITY,
            },
            GAS_PARSER_BASE_FIELD[-1]: {
                SCHEMA_TYPE_KEY: click.STRING,
                SCHEMA_HELP_KEY: "String that describes how to parse the gas-api for base fee.",
                SCHEMA_DEFAULT_KEY: DEFAULT_GAS_PARSER_BASE,
            },
        },
    },
    EMAIL_SECTION_KEY: {
        EMAIL_SENDER_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.STRING,
            SCHEMA_HELP_KEY: "Sender email for the Notification Service."
            " Requires a password from env vars.",
        },
        EMAIL_RECEIVERS_FIELD[-1]: {
            SCHEMA_TYPE_KEY: StringListParamType(separator=","),
            SCHEMA_HELP_KEY: "List of receivers for the Notification Service."
            " Use comma to pass multiple values. Will override config.json",
        },
        EMAIL_SMTP_SERVER_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.STRING,
            SCHEMA_HELP_KEY: "SMTP server to be used.",
            SCHEMA_DEFAULT_KEY: DEFAULT_EMAIL_SMTP_SERVER,
        },
        EMAIL_SMTP_PORT_FIELD[-1]: {
            SCHEMA_TYPE_KEY: click.INT,
            SCHEMA_HELP_KEY: "SMTP port to to be used on the given server.",
            SCHEMA_DEFAULT_KEY: DEFAULT_EMAIL_SMTP_PORT,
        },
    },
    WATCHERS_FIELD[-1]: {
        SCHEMA_TYPE_KEY: StringListParamType(separator=","),
        SCHEMA_HELP_KEY: "List of Watcher APIs to submit transactions."
        " Use comma to pass multiple values. Will override config.json",
    },
}
