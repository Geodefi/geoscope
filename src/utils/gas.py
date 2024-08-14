# -*- coding: utf-8 -*-
import struct
from geodefi.utils import wrappers
from geodefi import Geode

from src.common import AttributeDict
from src.exceptions import HighGasError, GasApiError
from src.globals import get_sdk, get_config, get_logger


def __float_to_hexstring(f):
    return hex(struct.unpack("<I", struct.pack("<f", f))[0])


@wrappers.http_request
def fetch_gas() -> tuple:
    _url: str = get_config().gas.api
    return (_url, True)


def parse_gas(gas) -> tuple[float]:
    __priority_fee: list = get_config().gas.parser.priority.split(".")
    gas_priority = gas
    for i in __priority_fee:
        gas_priority = gas_priority[i]

    __base_fee: list = get_config().gas.parser.base.split(".")
    gas_base_fee = gas
    for j in __base_fee:
        gas_base_fee = gas_base_fee[j]
    sdk: Geode = get_sdk()

    return sdk.w3.to_wei(gas_priority, "gwei"), sdk.w3.to_wei(gas_base_fee, "gwei")


def get_gas() -> tuple[str]:
    gas: AttributeDict = get_config().gas
    if gas:
        if gas.api and gas.parser and gas.max_priority and gas.max_fee:
            priority_fee, base_fee = 0, 0
            try:
                priority_fee, base_fee = parse_gas(fetch_gas())
            except Exception as e:
                raise GasApiError("Gas api did not respond") from e

            sdk: Geode = get_sdk()

            if (priority_fee > sdk.w3.to_wei(gas.max_priority, "gwei")) or (
                base_fee > sdk.w3.to_wei(gas.max_fee, "gwei")
            ):
                get_logger().critical(
                    f"Undesired GAS price => priority:{priority_fee}, fee:{base_fee}."
                    "Tx will not be submitted."
                )
                raise HighGasError("Gas prices are too high!")

            return __float_to_hexstring(priority_fee), __float_to_hexstring(base_fee)
    return (None, None)
