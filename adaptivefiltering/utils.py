import collections
import copy
import numpy as np
from geojson.utils import coords
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


def convert_segmentation(segmentation, srs_out, srs_in="EPSG:4326"):
    """
    This transforms the segmentation into a new spatial reference system.
        For this program all segmentations should be in EPSG:4326.
        :param segmentation:
            The segmentation that should be transformed
        :type: adaptivefiltering.segmentation.Segmentation


        :param srs_in:
            Current spatial reference system of the segmentation.
            Must be either EPSG or wkt.
        :type: str

        :param srs_out:
            Desired spatial reference system.
            Must be either EPSG or wkt.
        :type: str


        :return: Transformed segmentation.
        :rtype: adaptivefiltering.segmentation.Segmentation

    """

    from adaptivefiltering.segmentation import Segmentation
    from pyproj import Transformer

    new_features = copy.deepcopy(segmentation["features"])

    for feature, new_feature in zip(segmentation["features"], new_features):

        if feature["geometry"]["type"] == "Polygon":
            feature["geometry"]["coordinates"] = [feature["geometry"]["coordinates"]]
        polygon_list = []
        transformer = Transformer.from_crs(srs_in, srs_out)

        for polygon in feature["geometry"]["coordinates"]:

            polygon_list.append([])
            for hole in polygon:
                hole = np.asarray(hole)

                output_x, output_y = transformer.transform(hole[:, 0], hole[:, 1])
                polygon_list[-1].append(np.stack([output_x, output_y], axis=1).tolist())

        if feature["geometry"]["type"] == "Polygon":
            polygon_list = polygon_list[0]

        new_feature["geometry"]["coordinates"] = polygon_list

    return Segmentation(new_features)


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
