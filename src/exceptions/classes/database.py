# -*- coding: utf-8 -*-


class DatabaseError(Exception):
    """Exception raised for errors related with Database actions."""


class DatabaseMismatchError(DatabaseError):
    """Exception raised for errors related with Database mismatches."""
