# -*- coding: utf-8 -*-
# TODO: by copying stuff from avax, improve these... i don't even remember how we done those.


class PythonVersionException(Exception):
    "Python version is not supported"
    pass


class DeadDaemonException(Exception):
    "A previously stopped Deamon is being reinitiated."
    pass


class HttpRequestException(Exception):
    "Something wrong with the http request."
    pass


class CouldNotConnect(Exception):
    "Provided api URLs for the chain does not work like expected"
    pass


class DaemonStoppedException(Exception):
    "Exception in thread background"
    pass


class StateCreationException(Exception):
    "Provided arguments for the state is incorrect"
    pass


class DuplicateStateException(Exception):
    "Provided arguments for the state is already claimed by another instance"
    pass


class UnknownKeyException(Exception):
    "Provided value name does not exist according to the state structure"
    pass


class VerificationException(Exception):
    "Provided state does not have a way to verify"
