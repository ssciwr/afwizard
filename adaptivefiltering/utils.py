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


def stringify_value(value):
    """Stringify a value, making sequence space delimited"""
    if is_iterable(value):
        return " ".join(value)

    return str(value)


def reproject_dataset(dataset, out_srs, in_srs=None):
    """
    Standalone function to reproject a given dataset with the option of forcing a input_srs

    :parma out_srs: The desired output format. The default is the same one as in the interactive map.
    :type out_srs: string

    :param in_srs: The input format from wich the conversation is starting. The default is the the current srs.
    :type in_srs: string

    :return: A reprojected dataset
    :rtype: pdalInMemorydataset

    """
    from adaptivefiltering.pdal import execute_pdal_pipeline
    from adaptivefiltering.pdal import PDALInMemoryDataSet

    dataset = PDALInMemoryDataSet.convert(dataset)
    if in_srs is None:
        in_srs = dataset.spatial_reference

    config = {
        "type": "filters.reprojection",
        "in_srs": in_srs,
        "out_srs": out_srs,
    }
    pipeline = execute_pdal_pipeline(dataset=dataset, config=config)

    return PDALInMemoryDataSet(
        pipeline=pipeline,
        provenance=dataset._provenance
        + ["converted the dataset to the {} spatial reference.".format(out_srs)],
    )
