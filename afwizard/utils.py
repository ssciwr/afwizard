import collections
import re
import pyproj


class AFwizardError(Exception):
    pass


def is_iterable(object):
    """Whether the object is an iterable (excluding a string)"""
    return isinstance(object, collections.abc.Iterable) and not isinstance(object, str)


def stringify_parameters(value):
    """Stringify a value, making sequence space delimited"""
    if is_iterable(value):
        return sum((stringify_parameters(v) for v in value), [])

    return [str(value)]


def check_spatial_reference(crs):
    """Validate and normalize a given CRS string

    We accept either WKT or an EPSG code string of the form
    :code:`EPSG:xxxx{x}`.
    """
    if pyproj.crs.is_wkt(crs):
        return crs

    # if the EPSG code matches this pattern it will be reduced to just this.
    elif re.match("(?i)^EPSG:[0-9]{4,5}", crs):
        new_crs = re.match("(?i)^EPSG:[0-9]{4,5}", crs).group()
        if new_crs != crs:
            print(f"The given crs was reduced from {crs} to {new_crs}")

        return new_crs
    else:
        raise AFwizardError(
            f"The given crs is neither a WKT nor a 4 to 5 digit EPSG code, but is {crs}"
        )


def as_number_type(type_, value):
    """Transform a string to a number according to given type information"""
    if type_ == "integer":
        return int(value)
    elif type_ == "number":
        return float(value)
    else:
        raise NotImplementedError(f"as_number_type does not support type {type_}")
