import collections
import copy
import numpy as np
import re
import pyproj


class AdaptiveFilteringError(Exception):
    pass


def is_iterable(object):
    """Whether the object is an iterable (excluding a string)"""
    return isinstance(object, collections.abc.Iterable) and not isinstance(object, str)


def stringify_value(value):
    """Stringify a value, making sequence space delimited"""
    if is_iterable(value):
        return " ".join(value)

    return str(value)


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
        raise Exception(
            f"The given crs is neither a WKT nor a 4 to 5 digit EPSG code, but is {crs}"
        )


def merge_segmentation_features(seg):
    from adaptivefiltering.segmentation import Segmentation

    # if only one feature is present the segmentation will be returned as is.
    if len(seg["features"]) == 1:
        return seg

    # the metadata of the first feature is copied over.
    merged_seg = Segmentation([seg["features"][0].copy()])
    # from the copied feature the geometry is overriden to be a MultiPolygon
    merged_seg["features"][0]["geometry"] = {"type": "MultiPolygon", "coordinates": []}

    for features in seg["features"]:
        # geojson polygons should always be a three dimensional list, in case they have been reduced this will buffer them again
        if len(np.asarray(features["geometry"]["coordinates"]).shape) == 2:
            features["geometry"]["coordinates"] = [features["geometry"]["coordinates"]]
        for coords in features["geometry"]["coordinates"]:
            # the list brackets are necessary to avoid dimensional reduction
            # if this is not done the next polygon will be interpreted as a hole in the previous one.

            merged_seg["features"][0]["geometry"]["coordinates"].append([coords])

    return merged_seg


def as_number_type(type_, value):
    """Transform a string to a number according to given type information"""
    if type_ == "integer":
        return int(value)
    elif type_ == "number":
        return float(value)
    else:
        raise NotImplementedError(f"as_number_type does not support type {type_}")
