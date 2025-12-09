import re

EXPECTED_VERSION = "1.0.0"
SUBMIT_ENDPOINT = "/v1/submit"
VERSION_ENDPOINT = "/v1/version"
SIGNERS_ENDPOINT = "/v1/signers"
CONTRACT_ADDRESS_ENDPOINT = "/v1/contract-address"
CHAIN_ID_ENDPOINT = "/v1/chain-id"
HTTP_PATTERN = re.compile(
    r"^(?:http|https)://"
    r"(?:\S+(?::\S*)?@)?"
    r"(?:(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+"
    r"[A-Za-z]{2,6}"
    r"(?::\d{2,5})?"
    r"(?:/\S*)?$"
)
