import collections
import copy
import numpy as np
from geojson.utils import coords


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

    # for just a single srs_in
    for feature, new_feature in zip(segmentation["features"], new_features):
        feature_coords = np.asarray(list(coords(feature)))
        if len(feature_coords.shape) == 2:
            feature_coords = [feature_coords]
        new_feature["geometry"]["coordinates"] = []
        transformer = Transformer.from_crs(srs_in, srs_out)
        for coordinates in feature_coords:
            output_x, output_y = transformer.transform(
                coordinates[:, 0], coordinates[:, 1]
            )

            new_feature["geometry"]["coordinates"].append(
                np.stack([output_x, output_y], axis=1).tolist()
            )
    return Segmentation(new_features)
