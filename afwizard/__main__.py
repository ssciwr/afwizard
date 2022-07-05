from afwizard.dataset import DataSet
from afwizard.execute import apply_adaptive_pipeline
from afwizard.lastools import set_lastools_directory
from afwizard.library import add_filter_library
from afwizard.opals import set_opals_directory
from afwizard.segmentation import Segmentation
from afwizard.utils import check_spatial_reference

import click
import logging
import os
import re

logger = logging.getLogger("afwizard")


def locate_lidar_dataset(ctx, param, path):
    """Expand given data paths into a list of files"""

    # Validate that the file has the las or laz extension
    _, ext = os.path.splitext(path)
    if ext.lower() in (".las", ".laz"):
        return DataSet(os.path.abspath(path))
    else:
        raise click.BadParameter(f"Lidar datasets must be .las or .laz (not: {path})")


def validate_segmentation(ctx, param, filename):
    # Check that the file has the correct extension
    _, ext = os.path.splitext(filename)
    if ext.lower() != ".geojson":
        raise click.BadParameter(
            f"Segmentation files must be .geojson (not: {filename})"
        )

    # Try reading the content
    try:
        seg = Segmentation.load(filename)
    except:
        # TODO: Restrict the exception we are expecting here
        raise click.BadParameter(f"Segmentation file was not {filename} readable")

    return seg


def validate_suffix(ctx, param, suffix):
    if not re.fullmatch("[a-z0-9_]*", suffix):
        raise click.BadParameter(
            f"Suffix should consist of lowercase letters, numbers and underscores only"
        )
    return suffix


def validate_spatial_reference(ctx, param, crs):
    try:
        return check_spatial_reference(crs)
    except:
        raise click.BadParameter(
            f"Cannot validate spatial reference system '{crs}'. Use either WKT or 'EPSG:xxxx'"
        )


@click.command()
@click.option(
    "--dataset",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    callback=locate_lidar_dataset,
    help="The LAS/LAZ data file to work on.",
)
@click.option(
    "--dataset-crs",
    type=str,
    required=True,
    callback=validate_spatial_reference,
    help="The CRS of the data",
)
@click.option(
    "--segmentation",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    callback=validate_segmentation,
    help="The GeoJSON file that describes the segmentation of the dataset. This is expected to be generated either by the Jupyter UI or otherwise provide the necessary information about what filter pipelines to apply.",
)
@click.option(
    "--segmentation-crs",
    type=str,
    required=True,
    callback=validate_spatial_reference,
    help="The CRS used in the segmentation",
)
@click.option(
    "--library",
    type=click.Path(exists=True, file_okay=False),
    multiple=True,
    help="A filter library location that AFwizard should take into account. Can be given multiple times.",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False),
    default="output",
    help="The directory to place output files (both LAS/LAZ and GeoTiff).",
    show_default=True,
)
@click.option(
    "--resolution",
    type=click.FloatRange(min=0.0, min_open=True),
    default=0.5,
    help="The meshing resolution to use for generating GeoTiff files",
    metavar="FLOAT",
    show_default=True,
)
@click.option(
    "--compress",
    type=bool,
    is_flag=True,
    help="Whether LAZ files should be written instead of LAS.",
)
@click.option(
    "--suffix",
    type=str,
    default="filtered",
    help="The suffix to add to filtered datasets.",
    callback=validate_suffix,
    show_default=True,
)
@click.option(
    "--opals-dir",
    type=click.Path(file_okay=False, exists=True),
    help="The directory where to find an OPALS installation",
)
@click.option(
    "--lastools-dir",
    type=click.Path(file_okay=False, exists=True),
    help="The directory where to find a LASTools installation",
)
def main(**args):
    """Command Line Interface for AFwizard

    This CLI is used once you have finished the interactive exploration
    work with the AFwizard Jupyter UI. The CLI takes your dataset
    and the segmentation file created in Jupyter and executes the ground
    point filtering on the entire dataset.
    """

    # Register all filter libraries with AFwizard
    for lib in args.pop("library"):
        add_filter_library(path=lib)

    # Set the OPALS and LASTools paths
    set_opals_directory(args.pop("opals_dir"))
    set_lastools_directory(args.pop("lastools_dir"))

    # Add CRS to data and segmentation
    args["dataset"].spatial_reference = args.pop("dataset_crs")
    args["segmentation"].spatial_reference = args.pop("segmentation_crs")

    # Call Python API and log errors
    try:
        apply_adaptive_pipeline(**args)
    except Exception:
        logger.exception("AFwizard failed with the following error")


if __name__ == "__main__":
    main()
