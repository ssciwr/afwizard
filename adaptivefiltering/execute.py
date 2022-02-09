from adaptivefiltering.dataset import DataSet
from adaptivefiltering.filter import load_filter
from adaptivefiltering.library import locate_filter
from adaptivefiltering.paths import get_temporary_filename
from adaptivefiltering.segmentation import Segmentation
from adaptivefiltering.utils import AdaptiveFilteringError

import os
import subprocess


def apply_adaptive_pipeline(
    datasets=None,
    segmentation=None,
    output_dir="output",
    resolution=0.5,
    compress=False,
    suffix="filtered",
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
    :type compress: bool
    :param suffix:
        A suffix to use for files after applying filtering
    :type suffix: str
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

    # Determine the extension of LAS/LAZ files
    extension = "laz" if compress else "las"

    # We treat each given dataset file individually.
    for ds in datasets:
        # A data structure to store all the filtered bits in
        filtered_segments = []

        # We apply each segment individually
        for segment in segmentation:
            # Restrict the dataset to the subset
            rds = ds.restrict(Segmentation(segment))

            # Get the pipeline object for this filtering
            pipeline = load_filter(locate_filter(segment["properties"]["pipeline"]))

            # Apply!
            filtered = pipeline.execute(rds)

            # Save this to a file in order to be able to free memory
            filename = get_temporary_filename(extension=extension)
            saved = filtered.save(filename, compress=compress)
            del filtered

            filtered_segments.append(saved)

        # Join the segments in this dataset file. We use subprocess for this
        # because our PDAL execution code from Python is not really fit for
        # multiple input files.
        _, filename = os.path.split(ds.filename)
        filename, _ = os.path.splitext(filename)
        las_output = os.path.join(output_dir, f"{filename}_{suffix}.{extension}")
        subprocess.run(
            f"pdal merge {' '.join(ds.filename for ds in filtered_segments)} {las_output}"
        )

        # TODO: What derivative results do we want to generate. Or would it be quite
        #      normal to calculate these with a different tool.
