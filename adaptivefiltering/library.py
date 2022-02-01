from adaptivefiltering.filter import load_filter, save_filter
from adaptivefiltering.paths import load_schema
from adaptivefiltering.utils import is_iterable

import click
import collections
import glob
import importlib
import json
import jsonschema
import os
import pyrsistent


# The global storage for the list of directories
_filter_libraries = []


FilterLibrary = collections.namedtuple(
    "FilterLibrary", ["filters", "name", "path"], defaults=[[], None, ""]
)


def get_filter_libraries():
    return tuple(_filter_libraries)


def add_filter_library(path=None, package=None):
    """Add filters from a custom library

    :param path:
        The filesystem path where the filter library is located. The filter
        library is a directory containing a number of filter files and
        potentially a library.json file containing metadata.
    :type path: str
    :param package:
        Alternatively, you can specify a Python package that is installed on
        the system and that contains the relevant JSON files.
    :type package: str
    """
    # Translate a package name to a directory
    if package is not None:
        mod = importlib.import_module(package)
        package_path, _ = os.path.split(mod.__file__)
        return add_filter_library(path=package_path)

    # Look for a library metadata file
    metadata = {}
    if os.path.exists(os.path.join(path, "library.json")):
        # Load the meta data
        with open(os.path.join(path, "library.json"), "r") as f:
            metadata = json.load(f)

        # Validate the document against our schema
        schema = load_schema("library.json")
        jsonschema.validate(metadata, schema)

    # Iterate over the JSON documents in the directory and load them
    filters = []
    for filename in glob.glob(os.path.join(path, "*.json")):
        # If this is the library meta file, skip it
        if os.path.split(filename)[1] == "library.json":
            continue

        # If the title field has not been specified, use the filename
        filter_ = load_filter(filename)
        if filter_.title == "":
            md = filter_.config.get("metadata", pyrsistent.pmap())
            md = md.update({"title": filename})
            filter_ = filter_.copy(metadata=md)

        # Add it to our list of filters
        filters.append(filter_)

    # Register the library object if it is existent
    if metadata or filters:
        _filter_libraries.append(FilterLibrary(filters=filters, path=path, **metadata))


def library_keywords(libs=get_filter_libraries()):
    """Return a list of keywords used across one or more library

    :param libs:
        One or more filter libraries
    """

    # Make libs parameter a list if not already
    if not is_iterable(libs):
        libs = [libs]

    result = []
    for lib in libs:
        for f in lib.filters:
            result.extend(f.keywords)

    return list(set(result))


def reset_filter_libraries():
    """Reset registered filter libraries to the default ones"""
    # Remove all registered filter libraries
    global _filter_libraries
    _filter_libraries = []

    # Register default paths
    add_filter_library(path=os.getcwd())
    add_filter_library(package="adaptivefiltering_library")


@click.command()
@click.argument(
    "library_path", type=click.Path(exists=True, file_okay=False, writable=True)
)
def upgrade_filter_library(library_path):
    """Upgrades all filters in a library to the latest version of the data model

    :param path:
        The path of the filesystem where the filter library is located.
    :type path: str
    """

    for filename in glob.glob(os.path.join(library_path, "*.json")):
        # If this is the library meta file, skip it
        if os.path.split(filename)[1] == "library.json":
            continue

        # Add it to our list of filters
        save_filter(load_filter(filename), filename)


# Upon import, we immediately reset the filter library to the defaults
reset_filter_libraries()
