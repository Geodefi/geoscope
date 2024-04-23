# -*- coding: utf-8 -*-


# class PythonVersionException(Exception):
#     "Python version is not supported"


class DeadDaemonException(Exception):
    "A previously stopped Daemon is being reinitiated."


# class HttpRequestException(Exception):
#     "Something wrong with the http request."


class CouldNotConnect(Exception):
    "Provided api URLs for the chain does not work like expected"


class DaemonStoppedException(Exception):
    "Exception in thread background"


class StateCreationException(Exception):
    "Provided arguments for the state is incorrect"


class DuplicateStateException(Exception):
    "Provided arguments for the state is already claimed by another instance"


class UnknownKeyException(Exception):
    "Provided value name does not exist according to the state structure"


class VerificationException(Exception):
    "Provided state does not have a way to verify"
