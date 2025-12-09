from typing import Any, Iterable


def flatten(lst: Iterable[Iterable[Any]]) -> list[Any]:
    """
    Flatten a nested iterable -(one level deep)- into a single flat list.

    This function takes an iterable of iterables (e.g., list of lists, tuple of tuples) and
    flattens it into a single list containing all the elements from the nested iterables.

    Args:
        lst (Iterable[Iterable[Any]]): An iterable containing nested iterables to flatten.

    Returns:
        list[Any]: A flattened list containing all elements from the nested iterables.

    Examples:
        >>> flatten([[1, 2], [3, 4], [5]])
        [1, 2, 3, 4, 5]

        >>> flatten([('a', 'b'), ('c',), ('d', 'e')])
        ['a', 'b', 'c', 'd', 'e']

    Raises:
        TypeError: If the input is not an iterable.
    """
    if not isinstance(lst, Iterable):
        raise TypeError(f"Expected an iterable of iterables, got {type(lst).__name__}")

    return [element for inner_list in lst for element in inner_list]
