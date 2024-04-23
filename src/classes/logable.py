import os
import logging
from logging.handlers import TimedRotatingFileHandler

from ..globals.config import CONFIG


class Logable:
    def __init__(self, name: str) -> None:
        self.logger = Logable.initLogger(name)

    def log_on(self):
        self.logger.setLevel(CONFIG.logger.level)

    def log_off(self):
        self.logger.setLevel(51)

    @staticmethod
    def get_formatter(dateformat: str):
        fmt = "%(levelname)s [%(asctime)s] %(message)s"
        return logging.Formatter(fmt, datefmt=dateformat)

    @staticmethod
    def initLogger(
        log_filename: str,
        dir: str = CONFIG.logger.directory,
        fmt: str = CONFIG.logger.format,
        log_level: str = CONFIG.logger.level,
    ) -> logging.Logger:
        """
        Initialize a new Logger with a TimedRotatingFileHandler.

        Args:
            log_filename (str): The name of the log file.
            dir (str): The directory path for the log file (default is DIR).
            fmt (str): The log message format (default is taken from CONFIG.logger.format).
            log_level (str): The logging level (default is taken from CONFIG.logger.level).

        Returns:
            logging.Logger: The initialized logger.
        """

        # Formatter
        formatter = Logable.get_formatter(fmt)

        # TimedRotatingFileHandler
        time_rotating_file_handler = TimedRotatingFileHandler(
            os.path.join(dir, log_filename),
            when=CONFIG.logger.when,
            interval=CONFIG.logger.interval,
            backupCount=CONFIG.logger.backupCount,
        )
        time_rotating_file_handler.setFormatter(formatter)

        # Initialize logger
        logger = logging.getLogger(__name__)
        logger.addHandler(time_rotating_file_handler)
        logger.setLevel(log_level)

        return logger
