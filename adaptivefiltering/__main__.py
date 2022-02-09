from adaptivefiltering.dataset import DataSet
from adaptivefiltering.execute import apply_adaptive_pipeline
from adaptivefiltering.lastools import set_lastools_directory
from adaptivefiltering.library import add_filter_library
from adaptivefiltering.opals import set_opals_directory
from adaptivefiltering.segmentation import Segmentation

import click
import os
import re


def _locate_lidar_datasets(paths):
    for path in paths:
        if os.path.isfile(path):
            # Validate that the file has the las or laz extension
            _, ext = os.path.splitext(path)
            if ext.lower() in (".las", ".laz"):
                yield os.path.abspath(path)
            else:
                raise click.BadParameter(
                    f"Lidar datasets must be .las or .laz (not: {path})"
                )
        elif os.path.isdir(path):
            for filename in os.listdir(path):
                _, ext = os.path.splitext(filename)
                if ext.lower() in (".las", ".laz"):
                    yield os.path.abspath(os.path.join(path, filename))
        else:
            raise click.BadParameter(
                f"Cannot interpret path {path} - must be file or directory"
            )


def locate_lidar_datasets(ctx, param, paths):
    """Expand given data paths into a list of files"""

    # Expand the paths into a tuple of dataset files
    files = tuple(_locate_lidar_datasets(paths))

    # If no files were found, we throw an error
    if len(files) == 0:
        raise click.BadParameter(f"No LAS/LAZ files were found in given data paths")

    return files


def validate_segmentation(ctx, param, filename):
    # Check that the file has the correct extension
    _, ext = filename
    if ext.lower() != ".json":
        raise click.BadParameter(f"Segmentation files must be .json (not: {filename})")

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


@click.command()
@click.option(
    "--data",
    type=click.Path(exists=True),
    multiple=True,
    required=True,
    callback=locate_lidar_datasets,
    help="The data files to work on. This may either be an LAS/LAZ file or a directory containing such files. This argument can be given multiple times to provide multiple data files.",
)
@click.option(
    "--segmentation",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    callback=validate_segmentation,
    help="The GeoJSON file that describes the segmentation of the dataset. This is expected to be generated either by the Jupyter UI or otherwise provide the necessary information about what filter pipelines to apply.",
)
@click.option(
    "--library",
    type=click.Path(exists=True, file_okay=False),
    multiple=True,
    help="A filter library location that adaptivefiltering should take into account. Can be given multiple times.",
)
@click.option(
    "--dry-run",
    type=bool,
    is_flag=True,
    help="When given, adaptivefiltering does not perform any ground point filtering. Instead, it gives verbose information about what would be done if adaptivefiltering was run without the --dry-run flag.",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False),
    default="output",
    help="The directory to place output files (both LAS/LAZ and GeoTiff) should be placed.",
)
@click.option(
    "--resolution",
    type=click.FloatRange(min=0.0, min_open=True),
    default=0.5,
    help="The meshing resolution to use for generating GeoTiff files",
    metavar="FLOAT",
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
def main(
    data,
    segmentation,
    library,
    dry_run,
    output_dir,
    resolution,
    compress,
    suffix,
    opals_dir,
    lastools_dir,
):
    """Command Line Interface for adaptivefiltering

    This CLI is used once you have finished the interactive exploration
    work with the adaptivefiltering Jupyter UI. The CLI takes your dataset
    file(s) and the segmentation file created in Jupyter and executes the
    ground point filtering on the entire dataset.
    """

    # Register all filter libraries with adaptivefiltering
    for lib in library:
        add_filter_library(path=lib)

    # Set the OPALS and LASTools paths
    set_opals_directory(opals_dir)
    set_lastools_directory(lastools_dir)

    # Maybe print a list of data files that will be processed
    if dry_run:
        click.echo("The following data files will be read:")
        for filename in data:
            click.echo(f"* {filename}")
        click.echo()
    else:
        # Call Python API
        apply_adaptive_pipeline(
            datasets=[DataSet(ds) for ds in data],
            segmentation=segmentation,
            output_dir=output_dir,
            resolution=resolution,
            compress=compress,
            suffix=suffix,
        )


if __name__ == "__main__":
    main()
