from datetime import datetime


def is_valid_timestamp(timestamp_str: str) -> bool:
    """
    Checks if the given string is a valid timestamp in the expected format.
    """
    try:
        datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
        return True
    except ValueError:
        return False
