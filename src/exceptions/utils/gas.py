# -*- coding: utf-8 -*-


class HighGasError(Exception):
    """The gas price is too high."""


class GasApiError(Exception):
    """The gas api did not respond."""
