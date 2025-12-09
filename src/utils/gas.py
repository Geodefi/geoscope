import struct
from typing import Any, cast

from geodefi import Geode
from geodefi.utils.wrappers import http_request

from src.exceptions import GasApiError, HighGasError
from src.globals import get_config, get_logger, get_sdk
from src.globals.constants.config import (
    GAS_API_FIELD,
    GAS_MAX_BASE_FIELD,
    GAS_MAX_PRIORITY_FIELD,
    GAS_PARSER_BASE_FIELD,
    GAS_PARSER_PRIORITY_FIELD,
)


def __float_to_hexstring(f: float) -> str:
    """
    Convert a floating-point number to its hexadecimal string representation.

    This function packs a float into 4 bytes using little-endian format,
    unpacks it as an unsigned integer, and then converts it to a hexadecimal string.

    Args:
        f (float): The floating-point number to convert.

    Returns:
        str: The hexadecimal string representation of the float.

    Raises:
        struct.error: If packing or unpacking fails due to incorrect format.
    """
    if not isinstance(f, float):
        raise TypeError("Gas input must be a float, defined in gwei")
    return hex(struct.unpack("<I", struct.pack("<f", f))[0])


@http_request
def __fetch_gas() -> tuple:
    """
    Fetch the Gas API URL from the configuration and retreives it with a http GET request.

    Returns:
        tuple[str, bool]:Gas API URL, to be accepted by the http_request wrapper.
    """
    _url: str = get_config(field=GAS_API_FIELD)
    return (_url, True)


def fetch_gas() -> dict[Any, Any]:
    """
    A temporary solution until http_request decorator is fixed:
    Wrapper around fetch_gas to provide the correct return type.

    Returns:
        dict[Any, Any]: The response from the fetch_gas function.
    """
    return cast(dict[Any, Any], __fetch_gas())


def __get_nested_value(data: dict, path: str) -> Any:
    """Recursively fetch a nested value from a dictionary."""
    keys = path.split(".")
    result = data
    for key in keys:
        if not isinstance(result, dict) or key not in result:
            raise KeyError(f"Key '{key}' not found in the gas data")
        result = result[key]
    return result


def parse_gas(gas: dict) -> tuple[float, float]:
    """
    Parse the gas information from the fetched gas data.

    This function extracts the priority fee and base fee from the provided gas dictionary
    based on the parser paths defined in the configuration.
    Then, converts these fees from Gwei to Wei.

    Args:
        gas (dict): The gas data, in wei.

    Returns:
        tuple[float, float]: A tuple containing the priority fee and base fee in Wei.

    Raises:
        KeyError: If the specified parser paths are not found in the gas data.
        GasApiError: If the conversion of fees fails.
    """
    # Extract priority and base fees using the paths from the config
    __priority_path: str = get_config(field=GAS_PARSER_PRIORITY_FIELD)
    __base_path: str = get_config(field=GAS_PARSER_BASE_FIELD)

    gas_priority_res = __get_nested_value(gas, __priority_path)
    gas_base_fee_res = __get_nested_value(gas, __base_path)

    sdk: Geode = get_sdk()
    try:
        priority_fee_wei = sdk.w3.to_wei(number=gas_priority_res, unit="gwei")
        base_fee_wei = sdk.w3.to_wei(number=gas_base_fee_res, unit="gwei")
    except Exception as e:
        get_logger().error(f"Error converting gas fees to Wei: {e}")
        raise GasApiError("Failed to convert gas fees to Wei.") from e

    return priority_fee_wei, base_fee_wei


def get_gas() -> tuple[str | None, str | None]:
    """
    Retrieve and validate the current gas prices.

    This function fetches the gas prices from the Gas API, parses them, and compares
    the priority fee and base fee against the maximum allowed values defined in the configuration.
    If the fetched gas prices exceed the configured maximums, it logs a critical error
    and raises a `HighGasError`.

    Returns:
        tuple[str | None, str | None]: A tuple containing the priority fee and base fee
        as hexadecimal strings if within acceptable limits; otherwise, (None, None).

    Raises:
        GasApiError: If the Gas API does not respond or returns invalid data.
        HighGasError: If the fetched gas prices exceed the configured maximums.
    """
    if get_config(field=GAS_API_FIELD):
        priority_fee, base_fee = None, None
        try:
            priority_fee, base_fee = parse_gas(fetch_gas())
        except Exception as e:
            get_logger().error(f"Unexpected error while fetching gas: {e}")
            raise GasApiError("Unexpected error while fetching gas.") from e

        sdk: Geode = get_sdk()

        if (priority_fee > sdk.w3.to_wei(get_config(field=GAS_MAX_PRIORITY_FIELD), "gwei")) or (
            base_fee > sdk.w3.to_wei(get_config(field=GAS_MAX_BASE_FIELD), "gwei")
        ):
            get_logger().critical(
                f"Undesired GAS price => priority:{priority_fee}, fee:{base_fee}."
                "Tx will not be submitted."
            )
            raise HighGasError("Gas prices are too high!")

        if priority_fee and base_fee:
            get_logger().info(
                f"Gas prices: priority_fee={priority_fee} Wei, base_fee={base_fee} Wei."
            )
            return __float_to_hexstring(priority_fee), __float_to_hexstring(base_fee)
    return (None, None)
