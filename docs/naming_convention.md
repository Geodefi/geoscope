# Naming Convention

## Functions

> Note that, for example a utility function like *send_email* does not need to confirm to this standards.
> These are simple classifications for ease of mind.

### Initialization

- `init_x`: Initialize or set up initial state.
  - init_sdk
  - init_constants
  - init_config
  - init_dbs

### Database Interactions

- `create_x`: Create new table in the database.
  - create_withdrawals_table
  - create_validators_table
  - create_slots_table
  - create_pools_table
  - create_merkles_table
  - create_deposits_table

- `drop_x`: Remove table in the database.
  - drop_withdrawals_table
  - drop_validators_table
  - drop_slots_table
  - drop_pools_table
  - drop_merkles_table
  - drop_deposits_table

- `reinitialize_x`: Remove existing table and create a new one.
  - reinitialize_withdrawals_table
  - reinitialize_validators_table
  - reinitialize_slots_table
  - reinitialize_pools_table
  - reinitialize_merkles_table
  - reinitialize_deposits_table

- `read_x`: Retrieve data from the database.
  - read_validator_balances
  - read_proposed_validators
  - read_validators_by_pool
  - read_operator_id_by_beacon_index
  - read_max_slot
  - read_block_number
  - read_pool_count
  - read_all_pool_ids
  - read_latest_pool_data_batch
  - read_withdrawal_contract_address

- `insert_x`: Insert fresh data into the database.
  - insert_withdrawals_batch
  - insert_validators_batch
  - insert_slots_batch
  - insert_pools_info_batch
  - insert_merkle_tree_json
  - insert_deposits_batch

- `update_x`: Update existing records in the database.
  - update_portal_pools
  - update_portal_validators
  - update_beacon_constants
  - update_pool_ids
  - update_pool_data_batch

- `increase_x`: Increment existing records in the database.
  - increase_withdrawn_balances
  - increase_fee_recipient_balances

- `check_x_by_y`: Check if a record exists in database
  - check_withdrawal_by_slot
  - check_validator_by_pubkey
  - check_validator_by_beacon_index
  - check_pool_by_id
  - check_deposit_by_slot

- `filter_x_by_y`: Return list of values filtered by given y.
  - filter_slots_by_proposer

- `fill_x_table`: Populate tables with data.
  - fill_validators_table
  - fill_pools_table

### API/Blockchain Interactions

- `call_x`: Invoke an API endpoint or perform a blockchain call.
  - call_StakeParams
  
- `fetch_x`: Retrieve data from an API or blockchain.
  - fetch_gas
  - fetch_event_logs
  - fetch_beacon_data
  - fetch_slot
  - fetch_verification_index
  - fetch_oracle_update_timestamp
  - fetch_oracle_address
  - fetch_proposed_pubkeys
  - fetch_validator_parsed
  - fetch_fulfilled_ether_balance
  - fetch_portal_state
  - fetch_slots_batch
  - fetch_validators_batch
  - fetch_portal_state_batch
  - fetch_portal_validators_batch

- `transact_x`: Perform transactions on the blockchain.
  - transact_report_beacon

### Internal Functions

- `get_x`: Retrieve a value or property internally.
  - get_gas
  - get_version
  - get_merkle_refresh_rate
  - get_withdrawal_contract
  - get_config
  - get_sdk
  - get_constants
  - get_logger

- `set_x`: Assign a value or property internally.
  - set_*env_var*
  - set_config
  - set_sdk
  - set_constants
  - set_logger

- `load_x`: Retrieve a value or property from outside environment
  - load_env

- `apply_x`: Apply a function or transformation to data.
  - apply_config

- `compute_x`: Perform calculations or computations.
  - compute_deposit_domain
  - compute_deposit_fork_data_root
  - compute_signing_root
  - compute_effective_balance
  - compute_price
  - compute_recipient_fee
  - compute_effective_balances_batch
  - compute_prices_batch

- `process_x`: Process data internally.
  - process_slots
  - process_report_beacon
  - process_verifications
  - process_fee_recipients
  - process_deposits_batch
  - process_withdrawals_batch

- `filter_x`: Filter data based on specific criteria.
  - filter_withdrawals
  - filter_deposits

- `parse_x`: Parse or interpret data.
  - parse_gas

- `gather_x`: Collect data from multiple sources.
  - gather_validator_data_by_pool
  - gather_merkle_data
  - gather_pool_info
  - gather_pool_data
  - gather_all_events

- `check_x`: Check if an operation is allowed to be performed.
  - check_verify_validators

### Validation and Checking

- `verify_x`: Perform validations or checks.
  - verify_signature
  - verify_withdrawal_credentials
  - verify_validator
  - verify_validators_batch

- `detect_x`: Detect patterns or anomalies.
  - detect_theft

### Batch Operations

- `x_batch`: batch operations, mostly using multithread.
  - fetch_slots_batch
  - fetch_validators_batch
  - fetch_portal_validators_batch
  - fetch_portal_state_batch
  - compute_effective_balances_batch
  - compute_prices_batch
  - process_withdrawals_batch
  - verify_validators_batch
  - get_events_batch
  - filter_deposits_batch
