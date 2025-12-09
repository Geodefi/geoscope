class CallFailedError(Exception):
    """Exception raised for errors in the portal calls."""


class MultiSigError(Exception):
    """Exception raised when the provided signer is not a multisig member for the Oracle."""
