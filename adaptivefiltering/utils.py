import collections
import copy
import numpy as np


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

    from pyproj import Proj, transform

    new_features = copy.deepcopy(segmentation["features"])

    # for just a single srs_in
    for feature, new_feature in zip(segmentation["features"], new_features):

        p_in = Proj(srs_in)
        p_out = Proj(srs_out)

        if p_in != p_out:
            new_feature["geometry"]["coordinates"] = [
                # The transpose is necessary to keep the segmentation shape, but it introduces a problem with the map boundary visualisation.
                np.transpose(
                    transform(p_in, p_out, *zip(*np.squeeze(coordinates)))
                ).tolist()
                for coordinates in feature["geometry"]["coordinates"]
            ]

    return Segmentation(new_features)
