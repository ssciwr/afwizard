from afwizard.filter import load_filter, save_filter
from afwizard.paths import load_schema, download_test_file
from afwizard.utils import AFwizardError, is_iterable

import click
import hashlib
import glob
import importlib
import json
import jsonschema
import os
import pyrsistent


# Global storage for the list of directories
_filter_libraries = []

# Global storage for the current working library directory
_current_library = None


class FilterLibrary:
    def __init__(self, name=None, path="", recursive=False):
        self.name = name
        self.path = path
        self.recursive = recursive

    @property
    def filter_paths(self):
        result = {}

        # Iterate over the JSON documents in the directory and load them
        for filename in glob.glob(
            os.path.join(self.path, "*.json"), recursive=self.recursive
        ):
            # If this is the library meta file, skip it
            if os.path.split(filename)[1] == "library.json":
                continue

            # If the title field has not been specified, use the filename
            try:
                filter_ = load_filter(filename)
                if filter_.title == "":
                    md = filter_.config.get("metadata", pyrsistent.pmap())
                    md = md.update({"title": filename})
                    filter_ = filter_.copy(metadata=md)

                # Add it to our list of filters
                result[filename] = filter_
            except (KeyError, jsonschema.ValidationError):
                # We ignore the filter if it cannot be validated against our schema.
                # That is necessary to distinguish filter pipeline JSON data from
                # other JSON data e.g. segmentations.
                pass

        return result

    @property
    def filters(self):
        return self.filter_paths.values()


def get_filter_libraries():
    """Get a list of all filter libraries currently registered"""

    # The reversing implements priority ordering from user-defined to built-in
    return tuple(reversed(_filter_libraries))


def get_current_filter_library():
    """Get the user-defined 'current' filter library

    That filter library is used preferrably for saving filters.
    It can be set with :ref:~afwizard.set_current_filter_library.
    """
    return _current_library


def set_current_filter_library(path, create_dirs=False, name="My filter library"):
    """Set a library path that will be used to store filters in

    :param path:
        The path to store filters in. Might be an absolute path or
        a relative path that will be interpreted with respect to the
        current working directory.
    :type path: str
    :param create_dirs:
        Whether afwizard should create this directory (and
        potentially some parent directories) for you
    :type create_dirs: bool
    :param name:
        The display name of the library (e.g. in the selection UI)
    :type name: str
    """
    # Make path absolute
    path = os.path.abspath(path)

    # Ensure existence of the directory
    if not os.path.exists(path):
        if create_dirs:
            os.makedirs(path)
        else:
            raise AFwizardError(
                f"The given path does not exist and create_dirs was not set"
            )

    # Set the global variable
    global _current_library
    _current_library = path

    # Add the metadata file to the filter library directory
    if name is not None:
        with open(os.path.join(path, "library.json"), "w") as f:
            json.dump({"name": name}, f)

    # Register the filter library
    add_filter_library(path=path)


def add_filter_library(path=None, package=None, recursive=False, name=None):
    """Add a custom filter library to this session

    Adaptivefiltering keeps a list of filter libraries that it browses for
    filter pipeline definitions. This function adds a new directory to that
    list. You can use this to organize filter files on your hard disk.

    :param path:
        The filesystem path where the filter library is located. The filter
        library is a directory containing a number of filter files and
        potentially a library.json file containing metadata.
    :type path: str
    :param package:
        Alternatively, you can specify a Python package that is installed on
        the system and that contains the relevant JSON files. This is used for
        afwizards library of community-contributed filter pipelines.
    :type package: str
    :param recursive:
        Whether the file system should be traversed recursively from
        the given directory to find filter pipeline definitions.
    :type recursive: bool
    :param name:
        A display name to override the name provided by library metadata
    :type name: str
    """
    # Translate a package name to a directory
    if package is not None:
        mod = importlib.import_module(package)
        package_path, _ = os.path.split(mod.__file__)
        return add_filter_library(path=package_path, recursive=recursive, name=name)

    # Always make the library path absolute
    path = os.path.abspath(path)

    # If the path already exists across registered filter libraries,
    # there is nothing to do.
    for lib in get_filter_libraries():
        if lib.path == path:
            return

    # Look for a library metadata file
    metadata = {}
    if os.path.exists(os.path.join(path, "library.json")):
        # Load the meta data
        with open(os.path.join(path, "library.json"), "r") as f:
            metadata = json.load(f)

        # Validate the document against our schema
        schema = load_schema("library.json")
        jsonschema.validate(metadata, schema)

    # Maybe override the name field in metadata
    if name is not None:
        metadata["name"] = name

    # Register the library
    _filter_libraries.append(FilterLibrary(path=path, recursive=recursive, **metadata))


def library_keywords(libs=None):
    """Return a list of keywords used across one or more libraries

    :param libs:
        One or more filter libraries
    """

    # If no libraries are given, we use all of them
    if libs is None:
        libs = get_filter_libraries()

    # Make libs parameter a list if not already
    if not is_iterable(libs):
        libs = [libs]

    result = []
    for lib in libs:
        for f in lib.filters:
            result.extend(f.keywords)

    return list(set(result))


def locate_filter(filename):
    """Find a filter with a given filename across all filter libraries

    :param filename:
        The filename of the filter without any directories.
    :type filename: str
    """

    # If this is already an absolute path, we check its existence and return
    if os.path.isabs(filename):
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Filter file {filename} does not exist!")
        return filename

    # Find the file across all libraries
    for lib in get_filter_libraries():
        if os.path.exists(os.path.join(lib.path, filename)):
            return os.path.join(lib.path, filename)

    # Maybe this is a filter shipped as part of our testing data
    if os.path.exists(download_test_file(filename)):
        return download_test_file(filename)

    # If we have not found it by now, we throw an error
    raise FileNotFoundError(f"Filter file {filename} cannot be found!")


def metadata_hash(pipeline):
    """Calculate a hash value for the filter pipeline metadata"""
    metadata = pyrsistent.thaw(pipeline.config.get("metadata", {}))
    mrepr = repr({k: metadata[k] for k in sorted(metadata.keys())})
    return hashlib.sha1(mrepr.encode()).hexdigest()


def locate_filter_by_hash(hash):
    """Locate a filter across the filter libraries given a metadata hash

    :param hash:
        The hash that we are looking for.
    :type hash: str
    """

    # Collect all matches to throw a meaningful error
    found = []
    found_paths = []
    for lib in get_filter_libraries():
        for path, f in lib.filter_paths.items():
            if hash == metadata_hash(f):
                found.append(f)
                found_paths.append(path)

    if not found:
        raise FileNotFoundError(
            "A filter pipeline for your segmentation could not be located!"
        )
    if len(found) > 1:
        raise AFwizardError(
            f"Ambiguous pipeline metadata detected! Candidates: {', '.join(found_paths)}"
        )
    else:
        return found[0]


def reset_filter_libraries():
    """Reset registered filter libraries to the default ones

    The default libraries are the current working directory and the
    library of community-contributed filter pipelines provided by
    :code:`afwizard`.
    """
    # Remove all registered filter libraries
    global _filter_libraries
    _filter_libraries = []

    # Also reset the current filter library
    global _current_library
    _current_library = None

    # Register default paths
    add_filter_library(path=os.getcwd(), name="Current working directory")
    add_filter_library(package="afwizard_library")


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
