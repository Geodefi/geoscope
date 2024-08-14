# -*- coding: utf-8 -*-


class SDKError(Exception):
    """Exception raised for errors in the sdk initialization."""


class MissingPrivateKeyError(SDKError):
    """Exception raised for errors when private key is missing."""
