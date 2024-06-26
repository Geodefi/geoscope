# -*- coding: utf-8 -*-


def find_missing(lst: list) -> list:
    """Finds missing numbers in a list of ordered numbers.

    Args:
        lst (list): list of ordered numbers.

    Returns:
        list: list of missing numbers.
    """

    # finds missing numbers in a list of ordered numbers
    # ex. find_missing([1,2,4,5,7]) -> [3,6]

    return list(set(range(min(lst), max(lst))) - set(lst))
