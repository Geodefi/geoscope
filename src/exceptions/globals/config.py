class ConfigurationFileError(Exception):
    "An error occurred during configuration."


class ConfigurationFieldError(Exception):
    "Unexpected value provided for one of the required fields on configuration file."


class MissingConfigurationError(ConfigurationFieldError):
    "One of the required fields on configuration file is missing."


class ConfigVersionError(ConfigurationFieldError):
    "The provided value for Config Version is old or not supported."


class WatcherVersionError(ConfigurationFieldError):
    "One of the provided Watcher endpoints returns a wrong version for the api."


class WatcherNetworkError(ConfigurationFieldError):
    "One of the provided Watcher endpoints returns a wrong chain-id for the api."


class WatcherAddressError(ConfigurationFieldError):
    "One of the provided Watcher endpoints returns a wrong oracle address for the api."
