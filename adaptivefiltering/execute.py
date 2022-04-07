from adaptivefiltering.dataset import DataSet
from adaptivefiltering.library import (
    locate_filter_by_hash,
    add_filter_library,
)
from adaptivefiltering.logger import attach_file_logger
from adaptivefiltering.paths import get_temporary_filename, get_temporary_workspace
from adaptivefiltering.segmentation import Segmentation, merge_classes
from adaptivefiltering.utils import AdaptiveFilteringError, is_iterable
from adaptivefiltering.filter import save_filter

import os
import shutil
import subprocess
import logging

logger = logging.getLogger("adaptivefiltering")


def apply_adaptive_pipeline(
    dataset=None,
    segmentation=None,
    pipelines=None,
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
        One or more datasets of type :ref:`~adaptivefiltering.dataset.DataSet`.
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

    if not isinstance(dataset, DataSet):
        raise AdaptiveFilteringError(
            "Dataset are expected to be of type adaptivefiltering.DataSet"
        )

    if not isinstance(segmentation, Segmentation):
        raise AdaptiveFilteringError(
            "Segmentations are expected to be of type adaptivefiltering.segmentation.Segmentation"
        )

    # We decrease the logging level
    logger.setLevel(logging.INFO)

    # Ensure existence of output directory
    logger.info(f"Creating output directory {os.path.abspath(output_dir)}")
    os.makedirs(output_dir, exist_ok=True)

    # We add a file logging handler
    attach_file_logger(os.path.join(output_dir, "output.log"))

    # Determine the extension of LAS/LAZ files
    extension = "laz" if compress else "las"

    # Ensure that the segmentation contains pipeline information
    for s in segmentation["features"]:
        if "pipeline" not in s.get("properties", {}):
            raise AdaptiveFilteringError(
                "All features in segmentation are required to define the 'pipeline' property"
            )

    # if pipelines were given, add them to the filter library
    logger.info("Collecting filters.")

    if pipelines is not None:
        if not is_iterable(pipelines):
            pipelines = [pipelines]

        for pipeline in pipelines:
            save_filter(pipeline, get_temporary_filename(extension=".json"))

        add_filter_library(get_temporary_workspace())

    # Extract all filters needed
    filter_hashes = [s["properties"]["pipeline"] for s in segmentation["features"]]
    filters = {h: locate_filter_by_hash(h) for h in filter_hashes}

    logger.info("Split dataset into different parts to apply the pipelines.")
    # Merge segmentation by classes
    merged = merge_classes(segmentation, keyword="pipeline")
    hash_to_segmentation = {
        m["properties"]["pipeline"]: Segmentation(
            [m], spatial_reference=merged.spatial_reference
        )
        for m in merged["features"]
    }

    # Filter the dataset once per filter
    filtered_datasets = []
    for i, (hash, filter) in enumerate(filters.items()):

        logger.info(
            f"Running filter {filter.title if filter.title else ''} ({i+1}/{len(filters)})"
        )

        # Write the filter into the output directory
        # TODO: Change this filename from hash to the saved filename once it is implemented
        save_filter(filter, os.path.join(output_dir, f"{filter.title}.json"))

        # Apply the filter
        filtered = filter.execute(dataset)

        # Restrict the dataset
        restricted = filtered.restrict(segmentation=hash_to_segmentation[hash])

        # And write it to a temporary file
        filtered_datasets.append(
            restricted.save(get_temporary_filename(extension=extension))
        )

        # Remove temporary datasets to free memory
        del filtered
        del restricted

    # Join the segments in this dataset file. We use subprocess for this
    # because our PDAL execution code from Python is not really fit for
    # multiple input files.
    logger.info("Merging the dataset back together.")

    _, filename = os.path.split(dataset.filename)
    filename, _ = os.path.splitext(filename)
    las_output = os.path.join(output_dir, f"{filename}_{suffix}.{extension}")
    subprocess.run(
        f"pdal merge {' '.join(ds.filename for ds in filtered_datasets)} {las_output}".split()
    )

    # Provide GeoTiff output for this dataset
    logger.info(
        f"Write GeoTiff rasterization of the dataset with resolution={resolution}"
    )

    gtiff_output = os.path.join(output_dir, f"{filename}_{suffix}.tiff")
    merged = DataSet(las_output)
    rastered = merged.rasterize(resolution=resolution)
    shutil.move(rastered.filename, gtiff_output)
