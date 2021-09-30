import collections


class AdaptiveFilteringError(Exception):
    pass


def is_iterable(object):
    return isinstance(object, collections.abc.Iterable) and not isinstance(object, str)


def get_angular_resolution(res_meter):
    """Returns the approximate angular resolution on earth.
    This is only a rough approximation for the moment.
    https://www.usna.edu/Users/oceano/pguth/md_help/html/approx_equivalents.htm
    """
    return res_meter * 0.00001 / 1.11
