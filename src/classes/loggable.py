# -*- coding: utf-8 -*-
"""
    A helper class makes logging easier for other classes.

    Example:   
        self = Loggable(name="package_name")
        self.logger.critical('critical message')
"""

import os
import logging
from logging import StreamHandler, Formatter
from logging.handlers import TimedRotatingFileHandler
from ..globals import CONFIG


class Loggable:
    def __init__(self, name: str) -> None:
        self.logger = self.__get_logger(name)

    def __get_logger(self, name: str):
        logger = logging.getLogger(name=name)
        logging.basicConfig()
        logger.propagate = False

        # TODO add flag for --no-log-stream
        logger.addHandler(self.__get_stream_handler())
        # TODO add flag for --no-log-file
        logger.addHandler(self.__get_file_handler(name=name))

        return logger

    @property
    def __level(self):
        # TODO add env or config for --log-level
        level_name = "DEBUG"
        return logging.getLevelName(level_name)

    @property
    def __formatter(self):
        # TODO take both fmt date and fmt as in config etc.
        return Formatter(
            fmt="[%(asctime)s] %(levelname)-8s :: %(message)s",
            datefmt="%H:%M:%S",
        )

    def __get_stream_handler(self):
        sh = StreamHandler()
        sh.setFormatter(self.__formatter)
        sh.setLevel(self.__level)
        return sh

    def __get_file_handler(self, name: str):
        main_dir = CONFIG.directory
        log_dir = CONFIG.logger.directory
        path = os.path.join(main_dir, log_dir)
        if not os.path.exists(path):
            os.makedirs(path)
        fh = TimedRotatingFileHandler(
            os.path.join(path, name + ".log"),
            when=CONFIG.logger.when,
            interval=CONFIG.logger.interval,
            backupCount=CONFIG.logger.backupCount,
        )
        # fh.suffix = "%Y-%m-%d_%H-%M-%S"
        fh.suffix = "%Y-%m-%d"

        fh.setFormatter(self.__formatter)
        fh.setLevel(self.__level)
        return fh
