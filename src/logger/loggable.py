# -*- coding: utf-8 -*-

import os
from typing import Any
import logging
from logging import StreamHandler, Formatter
from logging.handlers import TimedRotatingFileHandler

from ..globals.config import CONFIG


class Loggable:
    """
    A class to create a logger object with given streams and files. Supposed to be used as a
    global var. Logger functions can also be directly reached.

    Example:
        logger = Loggable()
        logger.info("info message")
        logger.error("error message")

        OR

        from src.global.logger import log
        log.info("info message")
        log.error("error message")


    Attributes:
        logger (obj): Logger object to be used in the class.

    """

    def __init__(self) -> None:
        """Initializes a Loggable object."""
        logger: logging.Logger = self.__get_logger()
        logger.info("Initalized a global logger.")
        self.logger = logger

    def __get_logger(self) -> logging.Logger:
        """Initializes and returns a logger object with given streams and files.

        Returns:
            logging.Logger: Logger object to be used in the class.
        """

        logger: logging.Logger = logging.getLogger()
        logger.setLevel(self.__level)
        logger.propagate = False

        handlers: list = list()
        if CONFIG.logger.stream:
            stream_handler: StreamHandler = self.__get_stream_handler()
            handlers.append(stream_handler)
            logger.addHandler(stream_handler)
            logger.info(
                f"Logger is provided with a stream handler. Level: {self.__level}"
            )

        if CONFIG.logger.file:
            file_handler: TimedRotatingFileHandler = self.__get_file_handler()
            handlers.append(file_handler)
            logger.addHandler(file_handler)
            logger.info(
                f"Logger is provided with a file handler. Level: {self.__level}"
            )

        logging.basicConfig(handlers=handlers, force=True)
        return logger

    @property
    def __level(self) -> str:
        """Returns the logger level from user configuration.

        Returns:
            str: Logger level name
        """
        return CONFIG.logger.level

    @property
    def __formatter(self) -> Formatter:
        """Returns the logger formatter with Multithread support.

        Example formatted msg for stream:
            [01:35:56] STAKE                | INFO     :: 0 new verified public keys are detected.

        Returns:
            Formatter: Formatter object to be used in the logger.
        """

        return Formatter(
            fmt=f"[%(asctime)s] %(threadName)-25s | %(levelname)-8s :: %(message)s",
            datefmt="%H:%M:%S",
        )

    def __get_stream_handler(self) -> StreamHandler:
        """Returns an initialized Stream Handler.

        Returns:
            StreamHandler: Initialized and Configured Stream Handler
        """

        sh: StreamHandler = StreamHandler()
        sh.setFormatter(self.__formatter)
        sh.setLevel(self.__level)

        return sh

    def __get_file_handler(self) -> TimedRotatingFileHandler:
        """Returns an initialized File Handler.

        Returns:
            TimedRotatingFileHandler: Initialized and Configured File Handler
        """

        main_dir: str = CONFIG.directory
        log_dir: str = CONFIG.logger.directory
        path: str = os.path.join(main_dir, log_dir)
        if not os.path.exists(path):
            os.makedirs(path)
        prefix: str = "log"
        filename: str = os.path.join(path, prefix)
        fh: TimedRotatingFileHandler = TimedRotatingFileHandler(
            filename,
            when=CONFIG.logger.when,
            interval=CONFIG.logger.interval,
            backupCount=CONFIG.logger.backup,
        )

        fh.setFormatter(self.__formatter)
        fh.setLevel(self.__level)
        return fh

    def __getattr__(self, attr: str) -> Any:
        """Added so, `self.info()` can be used instead of `self.logger.<log_level>()`

        Args:
            attr (str): Attribute to be get.

        Returns:
            Any: Attribute of the object.
        """

        return getattr(self.logger, attr)
