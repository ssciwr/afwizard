from adaptivefiltering.dataset import DataSet
from adaptivefiltering.segmentation import Segmentation
from adaptivefiltering.utils import AdaptiveFilteringError


def apply_adaptive_pipeline(
    datasets=None,
    segmentation=None,
    output_dir="output",
    resolution=0.5,
    compress=False,
):
    """Python API to apply a fully configured adaptive pipeline

    This function implements the large scale application of a spatially
    adaptive filter pipeline to a potentially huge dataset. This can either
    be used from Python or through adaptivefiltering's command line interface.

    :param datasets:
        One or more datasets of type :ref:`~adaptivefilter.DataSet`.
    :type datasets: list
    :param segmentation:
        The segmentation that provides the geometric information about the spatial
        segmentation of the dataset and what filter pipelines to apply in which segments.
    :type segmentation: adaptivefiltering.segmentation.Segmentation
    :param output_dir:
        The output directory to place the generated output in. Defaults
        to a subdirectory 'output' within the current working directory/
    :type output_dir: str
    :param resolution:
        The resolution in meters to use when generating GeoTiff files.
    :type resolution: float
    :param compress:
        Whether to write LAZ files instead of LAS>
    :type compress: boll
    """

    if isinstance(datasets, DataSet):
        datasets = [datasets]

    for dataset in datasets:
        if not isinstance(dataset, DataSet):
            raise AdaptiveFilteringError(
                "Dataset are expected to be of type adaptivefiltering.DataSet"
            )

    if not isinstance(segmentation, Segmentation):
        raise AdaptiveFilteringError(
            "Segmentations are expected to be of type adaptivefiltering.segmentation.Segmentation"
        )

    print("Now doing work")
