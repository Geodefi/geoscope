from hexbytes import HexBytes

from geodefi.globals import Network

from src.globals import get_logger, get_sdk


def etherscan(function_name: str, tx_hash: HexBytes) -> None:
    """
    Log the Etherscan URL for a submitted transaction based on the network.

    Args:
        function_name (str): Name of the contract function invoked.
        tx_hash (HexBytes): Transaction hash.
    """

    network: Network = Network(get_sdk().network)

    if network == Network.holesky:
        get_logger().info(
            f"{function_name} tx is submitted: https://holesky.etherscan.io/tx/{tx_hash.hex()}"
        )
    elif network == Network.ethereum:
        get_logger().info(
            f"{function_name} tx is submitted: https://etherscan.io/tx/{tx_hash.hex()}"
        )
    else:
        get_logger().info(
            f"{function_name} tx is submitted: https://etherscan.io/tx/{tx_hash.hex()}"
        )
