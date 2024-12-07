def first(iterable):
    return next(iter(iterable))


def first_or_else(iterable, default):
    item = next(iter(iterable or []), None)
    if item is None:
        return default
    return item


def first_or_none(iterable):
    return first_or_else(iterable, None)
