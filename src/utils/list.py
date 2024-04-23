def find_missing(lst: list) -> list:
    # finds missing numbers in a list of ordered numbers
    # ex. find_missing([1,2,4,5,7]) -> [3,6]

    return set(range(min(lst), max(lst))) - set(lst)
    # is_sorted = all(lst[i] <= lst[i + 1] for i in range(len(lst) - 1))
    # if is_sorted:
    #     return [i for x, y in zip(lst, lst[1:]) for i in range(x + 1, y) if y - x > 1]
    # else:
    #     raise
