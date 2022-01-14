import collections
import copy
import numpy as np
from geojson.utils import coords
import re
import pyproj


class AdaptiveFilteringError(Exception):
    pass


def is_iterable(object):
    return isinstance(object, collections.abc.Iterable) and not isinstance(object, str)


def stringify_value(value):
    """Stringify a value, making sequence space delimited"""
    if is_iterable(value):
        return " ".join(value)

    return str(value)


def convert_Segmentation(segmentation, srs_out, srs_in="EPSG:4326"):
    from adaptivefiltering.segmentation import Segmentation
    from pyproj import Transformer

    new_features = copy.deepcopy(segmentation["features"])

    for feature, new_feature in zip(segmentation["features"], new_features):
        feature_coords = np.asarray(list(coords(feature)))
        # geojson requiere a 3d list, even if the outer most list is empty
        if len(feature_coords.shape) == 2:
            feature_coords = [feature_coords]

        new_feature["geometry"]["coordinates"] = []
        transformer = Transformer.from_crs(srs_in, srs_out)
        for coordinates in feature_coords:
            output_x, output_y = transformer.transform(
                coordinates[:, 0], coordinates[:, 1]
            )
            # the x and y arrays are merged into the new Segmentation.
            new_feature["geometry"]["coordinates"].append(
                np.stack([output_x, output_y], axis=1).tolist()
            )
    return Segmentation(new_features)


def check_spatial_reference(crs):
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
        # geojson Polygons should always be a 3 dim list, in case they have been reduced this will buffer them again
        if len(np.asarray(features["geometry"]["coordinates"]).shape) == 2:
            features["geometry"]["coordinates"] = [features["geometry"]["coordinates"]]
        for coords in features["geometry"]["coordinates"]:
            # the list brackets are necessary to avoid dimensional reduction
            # if this is not done the next polygon will be interpreted as a hole in the previous one.

            merged_seg["features"][0]["geometry"]["coordinates"].append([coords])

    return merged_seg
