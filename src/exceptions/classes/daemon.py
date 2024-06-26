# -*- coding: utf-8 -*-


class DaemonError(Exception):
    """Exception raised for errors in the Daemon class."""


class DaemonStoppedException(DaemonError):
    "Exception in thread background"
