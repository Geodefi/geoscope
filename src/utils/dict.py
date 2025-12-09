from typing import Any, Iterable


def set_nested_value(dct: dict, keys: list | tuple, value: Any) -> dict:
    """
    Given a dictionary `d`, a list of keys `keys`, and a value `value`,
    this function will set d[keys[0]][keys[1]]...[keys[-1]] = value.
    If any intermediate key does not exist, it will be created as an empty dictionary.
    """
    current = dct
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value
    return dct


def get_nested_value(dct: dict, keys: Iterable, abort: bool = True) -> Any:
    """Get a nested dictionary value by a list of keys. Return None if not found."""
    for k in keys:
        if not isinstance(dct, dict) or k not in dct:
            if abort:
                raise KeyError(repr(k))
            return None
        dct = dct[k]
    return dct
