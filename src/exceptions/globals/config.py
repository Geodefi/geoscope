# -*- coding: utf-8 -*-


class ConfigurationError(Exception):
    "An error occurred during configuration."


class MissingConfigurationError(ConfigurationError):
    "A required configuration is missing."


class ConfigurationFileError(ConfigurationError):
    "An error occurred while loading the configuration file."
