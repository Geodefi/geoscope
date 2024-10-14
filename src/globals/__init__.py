# -*- coding: utf-8 -*-
# pylint: disable=global-statement

# TODO: I need some tying here...

# global CONFIG referance that requires initialization
__CONFIG = None

# global SDK referance that requires initialization
__SDK = None

# global referance for Constant variables, which also requires initialization
__CONSTANTS = None

__LOGGER = None


def set_config(value):
    global __CONFIG
    __CONFIG = value


def get_config():
    return __CONFIG


def set_sdk(value):
    global __SDK
    __SDK = value


def get_sdk():
    return __SDK


def set_constants(value):
    global __CONSTANTS
    __CONSTANTS = value


def get_constants():
    return __CONSTANTS


def set_logger(value):
    global __LOGGER
    __LOGGER = value


def get_logger():
    return __LOGGER
