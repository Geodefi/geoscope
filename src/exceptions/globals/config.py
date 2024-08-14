# -*- coding: utf-8 -*-


class ConfigurationFileError(Exception):
    "An error occurred during configuration."


class MissingConfigurationError(Exception):
    "One of the required fields on configuration file is missing."


class ConfigurationFieldError(Exception):
    "The provided value for One of the required fields on configuration file is out of boundary."
