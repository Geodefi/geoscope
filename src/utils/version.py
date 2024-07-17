import sys

from src.exceptions.utils.version import PythonVersionException


def check_python_version() -> None:
    """Checks that the python version running is sufficient and exits if not."""

    if sys.version_info <= (3, 8) and sys.version_info >= (3, 10):
        raise PythonVersionException(
            f"Python version is not supported.Please consider using 3.8<>3.10"
        )
