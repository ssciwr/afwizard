from adaptivefiltering.filter import load_filter
from adaptivefiltering.paths import load_schema

import glob
import importlib
import json
import jsonschema
import os


# The global storage for the list of directories
_filter_libraries = []


class FilterLibrary:
    def __init__(self, filters=[], name=None):
        self.filters = filters
        self.name = name


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

        # Add it to our list of filters
        filters.append(load_filter(filename))

    # Register the library object if it is existent
    if metadata or filters:
        _filter_libraries.append(FilterLibrary(filters=filters, **metadata))


def reset_filter_libraries():
    """Reset registered filter libraries to the default ones"""
    # Remove all registered filter libraries
    global _filter_libraries
    _filter_libraries = []

    # Register default paths
    add_filter_library(os.getcwd())
    # TODO: Community library project


# Upon import, we immediately reset the filter library to the defaults
reset_filter_libraries()
