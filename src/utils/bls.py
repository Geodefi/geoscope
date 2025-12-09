from geodefi.globals.constants import DOMAIN_DEPOSIT, ZERO_BYTES32
from ssz.sedes.byte_vector import bytes4, bytes32, bytes48
from ssz.sedes.serializable import Serializable
from ssz.sedes.uint import uint64


class ForkData(Serializable):
    """
    Represents the fork data structure in the Beacon Chain.
    It used to compute the fork data root necessary for domain computations in deposit operations.

    Reference:
        https://github.com/ethereum/consensus-specs/blob/dev/specs/phase0/beacon-chain.md#forkdata
    """

    fields = [
        ("current_version", bytes4),
        ("genesis_validators_root", bytes32),
    ]


class SigningData(Serializable):
    """
    Represents the signing data structure used for creating signing roots.
    It includes the object root and the domain, which are essential for
    generating the signing root required for validators to sign messages.

    Reference:
        https://github.com/ethereum/consensus-specs/blob/dev/specs/phase0/beacon-chain.md#signingdata
    """

    fields = [
        ("object_root", bytes32),
        ("domain", bytes32),
    ]


class DepositMessage(Serializable):
    """
    Represents a deposit message in the Beacon Chain.

    This class defines the structure of a deposit message, including the validator's public key,
    withdrawal credentials, and the deposit amount. It is used to serialize and deserialize
    deposit data as per the Beacon Chain specifications.

    Reference:
        https://github.com/ethereum/consensus-specs/blob/dev/specs/phase0/beacon-chain.md#depositmessage
    """

    fields = [
        ("pubkey", bytes48),
        ("withdrawal_credentials", bytes32),
        ("amount", uint64),
    ]


def compute_deposit_domain(fork_version: bytes) -> bytes:
    """
    Compute the deposit domain based on the provided fork version.

    This function calculates the domain used specifically for deposit operations by combining
    the deposit domain type with the fork data root derived from the fork version.

    Args:
        fork_version (bytes): The current fork version in bytes. Must be exactly 4 bytes.

    Returns:
        bytes: The computed deposit domain.

    Raises:
        ValueError: If the fork_version is not exactly 4 bytes long.
    """
    if len(fork_version) != 4:
        raise ValueError(f"Fork version should be exactly 4 bytes. Got {len(fork_version)}")
    domain_type = DOMAIN_DEPOSIT
    fork_data_root = compute_deposit_fork_data_root(fork_version)
    return domain_type + fork_data_root[:28]


def compute_deposit_fork_data_root(current_version: bytes) -> bytes:
    """
    Compute the root of the ForkData structure for deposit operations.

    This function creates a ForkData instance with the current fork version and a fixed
    genesis validators root, then computes its SSZ hash tree root.

    Args:
        current_version (bytes): The current fork version in bytes. Must be exactly 4 bytes.

    Returns:
        bytes: The SSZ hash tree root of the ForkData instance.

    Raises:
        ValueError: If the current_version is not exactly 4 bytes long.
    """
    genesis_validators_root = ZERO_BYTES32  # Fixed value for deposit operations
    if len(current_version) != 4:
        raise ValueError(f"Fork version should be exactly 4 bytes. Got {len(current_version)}")
    fork_data = ForkData(
        current_version=current_version,
        genesis_validators_root=genesis_validators_root,
    )
    return fork_data.hash_tree_root


def compute_signing_root(ssz_object: Serializable, domain: bytes) -> bytes:
    """
    Compute the signing root of an SSZ object using the provided domain.

    The signing root is the hash tree root of a SigningData structure that includes the
    object's root and the domain. This is used for creating signatures that are domain-specific.

    The root is the hash tree root of:
    https://github.com/ethereum/consensus-specs/blob/dev/specs/phase0/beacon-chain.md#signingdata

    Args:
        ssz_object (Serializable): The SSZ-serializable object for which to compute the signing root
        domain (bytes): The domain in bytes. Must be exactly 32 bytes

    Returns:
        bytes: The computed signing root.

    Raises:
        ValueError: If the domain is not exactly 32 bytes long.
    """
    if len(domain) != 32:
        raise ValueError(f"Domain should be exactly 32 bytes. Got {len(domain)}")
    domain_wrapped_object = SigningData(
        object_root=ssz_object.hash_tree_root,
        domain=domain,
    )
    return domain_wrapped_object.hash_tree_root
