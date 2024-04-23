# -*- coding: utf-8 -*-
"""
    A helper class makes database management easier for other classes..

    Example:   
        with Database() as db:
            db.execute("SQL QUERY")
"""

import os
import sqlite3 as sql
from ..globals import CONFIG


class Database:
    def __init__(self, db_name) -> None:
        main_dir = CONFIG.directory
        db_dir = CONFIG.database.directory
        db_ext = ".db"

        path = os.path.join(main_dir, db_dir)
        if not os.path.exists(path):
            os.makedirs(path)

        try:
            # log(sql.version) #pyselite version
            # log(sql.sqlite_version) #SQLLite engine version
            self.connection = sql.connect(os.path.join(path, db_name + db_ext))
            self.cursor = self.connection.cursor()
        except Exception as e:
            raise e

    def __enter__(self):
        return self

    def __exit__(self, ext_type, exc_value, traceback):
        self.cursor.close()
        if isinstance(exc_value, Exception):
            self.connection.rollback()
        else:
            self.connection.commit()
        self.connection.close()

    def __getattr__(self, attr):
        return getattr(self.cursor, attr)
