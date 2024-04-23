class AttributeDict(dict):
    """
    AttributeDict allows dot notation on native dicts
    d["x"]["y"]["z"]
    d.x.y.z
    """

    __slots__ = ()
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


def convert_recursive(d: dict) -> AttributeDict:
    """
    recursively converts intertwined dicts into AttributeDict
    """
    for k, v in d.items():
        if isinstance(v, dict):
            d[k] = convert_recursive(v)
    return AttributeDict(**d)
