class WatcherApiError(Exception):
    """Exception raised for errors in the Watcher Api calls."""


class RequestException(Exception):
    """If a network-related error occurs during the Watcher requests."""
