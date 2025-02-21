import itertools


def first(iterable):
    return next(iter(iterable))


def first_or_else(iterable, default):
    item = next(iter(iterable or []), None)
    if item is None:
        return default
    return item


def first_or_none(iterable):
    return first_or_else(iterable, None)


def as_lists(*args):
    """Convert any input objects to list objects."""
    for item in args:
        yield item if isinstance(item, list) else [item]


def as_list(*args):
    """
    Convert any input objects to a single merged list object.

    Example:
    >>> as_list('foo', ['buzz', 'bizz'], 'bazz', 'bozz', ['bar'], ['bur'])
    ['foo', 'buzz', 'bizz', 'bazz', 'bozz', 'bar', 'bur']
    """
    if args == (None,):
        return []
    return list(itertools.chain.from_iterable(as_lists(*args)))
