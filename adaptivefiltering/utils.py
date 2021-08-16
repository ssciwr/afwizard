import collections


class AdaptiveFilteringError(Exception):
    pass


def is_iterable(object):
    if isinstance(object, collections.abc.Iterable) and not isinstance(object, str):
        return True
    else:
        return False
