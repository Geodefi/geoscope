# -*- coding: utf-8 -*-


def flatten(lst: list[list]) -> list:
    """Flattens a list of list into a single list

    Args:
        lst (list[list]): list of lists to flatten

    Returns:
        list: flattened list
    """
    return [element for inner_list in lst for element in inner_list]
