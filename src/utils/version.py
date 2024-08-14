# -*- coding: utf-8 -*-
# pylint: disable=import-outside-toplevel
import sys
from geodefi.exceptions import PythonVersionError


def check_python_version() -> None:
    """Checks that the python version running is sufficient and exits if not."""

    if sys.version_info <= (3, 8) and sys.version_info >= (3, 12):
        raise PythonVersionError(f"Python version is not supported.Please consider using 3.8<>3.12")


def get_version():
    try:
        try:
            from pathlib import Path
            import tomli

            pyproject_toml_file = Path(__file__).parent.parent / "pyproject.toml"
            if pyproject_toml_file.exists() and pyproject_toml_file.is_file():
                with open("pyproject.toml", mode="rb") as config:
                    toml_file = tomli.load(config)
                    return toml_file["tool"]["poetry"]["version"]
            else:
                raise Exception
        except Exception:
            import importlib

            return importlib.metadata.version("geonius")
    except Exception:
        return "1.0.0"
