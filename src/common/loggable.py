import logging
import os
from logging import Logger, StreamHandler, getLogger
from logging.handlers import TimedRotatingFileHandler
from typing import Any

from tqdm import tqdm

from src.globals.constants.config import (
    DEFAULT_LOGGER_BACKUP_KEEP,
    DEFAULT_LOGGER_BACKUP_WHEN,
    DEFAULT_LOGGER_DIR,
    DEFAULT_LOGGER_FORMAT_DATE,
    DEFAULT_LOGGER_FORMAT_MESSAGE,
    DEFAULT_LOGGER_LEVEL,
)

DEBUG_COLOR = "\x1b[38;20m"
INFO_COLOR = "\x1b[38;20m"
WARNING_COLOR = "\x1b[33;20m"
ERROR_COLOR = "\x1b[31;20m"
CRITICAL_COLOR = "\x1b[31;1m"
RESET = "\x1b[0m"


class CustomFormatter(logging.Formatter):
    """
    Custom formatter for log messages with color-coded output based on log levels.

    Args:
        fmt (str): Format string for log messages.
        datefmt (str): Format string for log timestamps.

    Methods:
        format(record: Any) -> Any:
            Formats the log record with the appropriate color based on its level.
            Overrides logging.Formatter.format.
    """

    def __init__(self, fmt: str, datefmt: str) -> None:
        super().__init__()

        self.formats = {
            logging.DEBUG: DEBUG_COLOR + fmt + RESET,
            logging.INFO: INFO_COLOR + fmt + RESET,
            logging.WARNING: WARNING_COLOR + fmt + RESET,
            logging.ERROR: ERROR_COLOR + fmt + RESET,
            logging.CRITICAL: CRITICAL_COLOR + fmt + RESET,
        }
        self.datefmt = datefmt

    def format(self, record: Any) -> Any:
        formatter = logging.Formatter(
            fmt=self.formats.get(record.levelno),
            datefmt=self.datefmt,
        )
        return formatter.format(record)


class TqdmLoggingHandler(StreamHandler):
    """
    Logging handler that integrates with tqdm to prevent interference with progress bars.

    Args:
        level (int): Logging level, defaulting to NOTSET.

    Methods:
        emit(record: Any) -> None:
            Emits a log record, ensuring compatibility with tqdm progress bars.
    """

    def __init__(self, level: int = logging.NOTSET):
        super().__init__(level)

    def emit(self, record: Any) -> None:
        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        # pylint: disable-next=broad-exception-caught
        except Exception:
            self.handleError(record)


class Loggable:
    """
    A class to create and manage a logger object with configurable stream and file handlers.
    Intended to be used as a global logger instance. Logger methods can be accessed directly.

    Example:
        logger = Loggable(main_dir="/path/to/geoscope").logger
        logger.info("Info message")
        logger.error("Error message")

    Attributes:
        logger (Logger): The configured logger instance.
        level (str): Logger level. [DEBUG, INFO, WARNING, ERROR, CRITICAL]

    """

    def __init__(
        self,
        main_dir: str,
        log_dir: str = DEFAULT_LOGGER_DIR,
        prefix: str = "log",
        level: str = DEFAULT_LOGGER_LEVEL,
        fmt: str = DEFAULT_LOGGER_FORMAT_MESSAGE,
        datefmt: str = DEFAULT_LOGGER_FORMAT_DATE,
        backup_when: str = DEFAULT_LOGGER_BACKUP_WHEN,
        backup_keep: int = DEFAULT_LOGGER_BACKUP_KEEP,
    ) -> None:
        """
        Initialize the Loggable instance with specified logging settings.

        Args:
            main_dir (str): Base directory where log files will be stored.
            log_dir (str): Subdirectory for storing log files.
             Default is defined by constants.
            prefix (str): Prefix for log file names.
             Default is "log".
            level (str): Logging level (e.g., DEBUG, INFO).
             Default is defined by constants.
            fmt (str): Log message format. Default is defined by constants.
            datefmt (str): Timestamp format for log messages.
             Default is defined by constants.
            backup_when (str): Time interval for rotating log files.
             Default is defined by constants.
            backup_keep (int): Maximum number of backup log files to retain.
             Default is defined by constants.

        Raises:
            ValueError: If an invalid logging level is provided.
        """
        self.level = level

        log_dir_path: str = os.path.join(main_dir, log_dir)
        os.makedirs(log_dir_path, exist_ok=True)
        log_file_path: str = os.path.join(log_dir_path, prefix)

        logger: Logger = self.__get_logger(log_file_path, fmt, datefmt, backup_when, backup_keep)
        logger.debug("Initalized a global logger.")
        self.logger: Logger = logger

    def __get_logger(
        self, file_path: str, fmt: str, datefmt: str, backup_when: str, backup_keep: int
    ) -> Logger:
        """
        Configures and returns a logger instance with specified handlers.

        Args:
            file_path (str): Complete file path and name for the file handler.
            fmt (str): Message format for the logger.
            datefmt (str): Date format for the logger messages.
            backup_when (str): When logger backups the current file and continue on a new file.
            backup_keep (int): Max logger files that will be kept. Oldest ones will be deleted.

        Returns:
            Logger: Configured Logger object.
        """
        logger: Logger = getLogger(__name__)

        level: str = self.level.upper()
        if level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid logging level: {level}")
        logger.setLevel(level)

        logger.propagate = False
        if logger.hasHandlers():
            logger.handlers.clear()
        handlers: list = []

        stream_handler: StreamHandler = self.__get_stream_handler(fmt, datefmt)
        handlers.append(stream_handler)
        logger.addHandler(stream_handler)
        logger.debug(f"Logger is provided with a stream handler. Level: {level}")

        file_handler: TimedRotatingFileHandler = self.__get_file_handler(
            file_path, fmt, datefmt, backup_when, backup_keep
        )
        handlers.append(file_handler)
        logger.addHandler(file_handler)
        logger.debug(f"Logger is provided with a file handler. Level: {level}")

        logging.basicConfig(handlers=handlers, force=True)  # Remove this in case of an error.
        return logger

    def __get_stream_handler(self, fmt: str, datefmt: str) -> StreamHandler:
        """
        Creates and returns a stream handler for logging to the console.

        Args:
            fmt (str): Message format for the logger.
            datefmt (str): Date format for the logger messages.

        Returns:
            StreamHandler: Configured StreamHandler.
        """
        sh: StreamHandler = TqdmLoggingHandler()
        sh.setFormatter(CustomFormatter(fmt=fmt, datefmt=datefmt))
        sh.setLevel(self.level)

        return sh

    def __get_file_handler(
        self, file_path: str, fmt: str, datefmt: str, backup_when: str, backup_keep: int
    ) -> TimedRotatingFileHandler:
        """
        Creates and returns a file handler with timed log rotation.

        Args:
            file_path (str): Complete file path and name for the file handler.
            fmt (str): Message format for the logger.
            datefmt (str): Date format for the logger messages.
            backup_when (str): When logger backups the current file and continue on a new file.
            backup_keep (int): Max logger files that will be kept. Oldest ones will be deleted.

        Returns:
            TimedRotatingFileHandler: Configured File Handler.
        """

        fh: TimedRotatingFileHandler = TimedRotatingFileHandler(
            file_path,
            when=backup_when,
            backupCount=backup_keep,
        )

        fh.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
        fh.setLevel(self.level)
        return fh
