"""
Constants used across the database modules. 
Contains schema keys, table names, and field names. 
These constants help maintain consistency and avoid hardcoding strings throughout the codebase.
"""

# Main Constants
SQL_CONNECTION_TIMEOUT = 30.0

# SCHEMA KEYS
SCHEMA_TYPE_KEY = "type"
SCHEMA_SQL_TYPE_KEY = "sql_type"
SCHEMA_CONSTRAINTS_KEY = "constraints"

# Keys for the Merkles table
MERKLES_TABLE_KEY = "Merkles"
MERKLES_ROOT_HASH_FIELD = "root_hash"
MERKLES_TREE_JSON_FIELD = "tree_json"

# Keys for the Deposits table
DEPOSITS_TABLE_KEY = "Deposits"
DEPOSITS_PUBKEY_FIELD = "pubkey"
DEPOSITS_SLOT_FIELD = "slot"
DEPOSITS_AMOUNT_FIELD = "amount"
DEPOSITS_WITHDRAWAL_CREDENTIALS_FIELD = "withdrawal_credentials"
DEPOSITS_SIGNATURE_FIELD = "signature"

# Keys for the Withdrawals table
WITHDRAWALS_TABLE_KEY = "Withdrawals"
WITHDRAWALS_VALIDATOR_INDEX_FIELD = "validator_index"
WITHDRAWALS_SLOT_FIELD = "slot"
WITHDRAWALS_ADDRESS_FIELD = "address"
WITHDRAWALS_AMOUNT_FIELD = "amount"

POOLS_TABLE_KEY = "Pools"
POOLS_POOL_ID_FIELD = "pool_id"
POOLS_NAME_FIELD = "name"
POOLS_WITHDRAWAL_CONTRACT_ADDRESS_FIELD = "withdrawal_contract_address"
POOLS_WITHDRAWAL_CREDENTIALS_FIELD = "withdrawal_credentials"
POOLS_PRICE_FIELD = "price"
POOLS_TOTAL_SUPPLY_FIELD = "total_supply"
POOLS_SURPLUS_FIELD = "surplus"
POOLS_SECURED_FIELD = "secured"
POOLS_FULFILLED_ETHER_BALANCE_FIELD = "fulfilled_ether_balance"

# Keys for the Slots table
SLOTS_TABLE_KEY = "Slots"
SLOTS_SLOT_FIELD = "slot"
SLOTS_BLOCK_NUMBER_FIELD = "block_number"
SLOTS_PROPOSER_INDEX_FIELD = "proposer_index"
SLOTS_FEE_RECIPIENT_FIELD = "fee_recipient"
SLOTS_BURNED_AMOUNT_FIELD = "burned_amount"

# Keys for the Validators table
VALIDATORS_TABLE_KEY = "Validators"
VALIDATORS_PUBKEY_FIELD = "pubkey"
VALIDATORS_PORTAL_INDEX_FIELD = "portal_index"
VALIDATORS_POOL_ID_FIELD = "pool_id"
VALIDATORS_OPERATOR_ID_FIELD = "operator_id"
VALIDATORS_POOL_FEE_FIELD = "pool_fee"
VALIDATORS_OPERATOR_FEE_FIELD = "operator_fee"
VALIDATORS_INFRASTRUCTURE_FEE_FIELD = "infrastructure_fee"
VALIDATORS_SIGNATURE31_FIELD = "signature31"
VALIDATORS_BEACON_INDEX_FIELD = "beacon_index"
VALIDATORS_WITHDRAWAL_CREDENTIALS_FIELD = "withdrawal_credentials"
VALIDATORS_EXIT_EPOCH_FIELD = "exit_epoch"
VALIDATORS_STAKE_SIGNATURE_FIELD = "stake_signature"
VALIDATORS_PROPOSAL_SIGNATURE_FIELD = "proposal_signature"
VALIDATORS_PROPOSAL_SLOT_FIELD = "proposal_slot"
VALIDATORS_WITHDRAWN_BALANCE_FIELD = "withdrawn_balance"
VALIDATORS_LAST_WITHDRAWN_FIELD = "last_withdrawn"
VALIDATORS_FEE_RECIPIENT_BALANCE_FIELD = "fee_recipient_balance"
