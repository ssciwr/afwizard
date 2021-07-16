import functools
import json
import os
import platform
import tempfile
import uuid
import xdg

# Storage for the temporary workspace directory
_tmp_dir = None

# Storage for the data directory that will be used to resolve relative paths
_data_dir = None


def set_data_directory(directory):
    """Set a custom root directory to locate data files

    :param directory: The custom data directory
    :type directory: str
    """
    global _data_dir
    _data_dir = directory


def get_temporary_filename(extension=""):
    """Create a filename for a temporary file

    Note, the file is not generated, but only a random filename is generated
    and it is ensured, that its directory is correctly created.
    """
    # Make sure that the temporary workspace exists
    global _tmp_dir
    if _tmp_dir is None:
        _tmp_dir = tempfile.TemporaryDirectory()

    return os.path.join(_tmp_dir, f"{uuid.uuid4()}.{extension}")


def locate_file(filename):
    """Locate a file on the filesystem

    This function abstracts the resolution of paths given by the user.
    It should be used whenever data is loaded from user-provided locations.
    The priority list for path resolution is the following:

    * If the given path is absolute, it is used as is.
    * If a path was set with :any:`set_data_directory` check whether
      the given relative path exists with respect to that directory
    * Check whether the given relative path exists with respect to
      the current working directory
    * Check whether the given relative path exists with respect to
      the specified XDG data directory (e.g. through the environment
      variable :code:`XDG_DATA_DIR`) - Linux/MacOS only.
    * Check whether the given relative path exists with respect to
      the package installation directory. This can be used to write
      examples that use package-provided data.

    :param filename: The (relative) filename to resolve
    :type filename: str
    :raises FileNotFoundError: Thrown if all resolution methods fail.
    :returns: The resolved, absolute filename
    """
    # If the path is absolute, do not change it
    if os.path.isabs(filename):
        return filename

    # Gather a list of candidate paths for relative path
    candidates = []

    # If set_data_directory was called, its result should take precedence
    if _data_dir is not None:
        candidates.append(os.path.join(_data_dir, filename))

    # Use the current working directory
    candidates.append(os.path.join(os.getcwd(), filename))

    # Use the XDG data directories
    if platform.system() in ["Linux", "Darwin"]:
        for xdg_dir in xdg.xdg_data_dirs():
            candidates.append(os.path.join(xdg_dir, filename))

    # Use the package installation directory
    candidates.append(os.path.join(os.path.split(__file__)[0], filename))

    # Iterate through the list to check for file existence
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    raise FileNotFoundError(
        f"Cannot locate file {filename}, maybe use set_data_directory to point to the correct location. Tried the following: {', '.join(candidates)}"
    )


@functools.lru_cache
def load_schema(schema):
    """Load a schema JSON file by inspecting the Python package installation

    :arg schema:
        The relative path of the schema in the schema directory.
    :type schema: str
    :return:
        The schema dictionary
    """
    # Resolve the relative path with respect to the package installation directory
    schema_store = os.path.join(os.path.split(__file__)[0], "schema")
    path = os.path.join(schema_store, schema)

    # Check for existence of the file
    if not os.path.exists(path):
        raise FileNotFoundError(f"Requested schema '{schema}' was not found!")

    # Read the file
    with open(path, "r") as f:
        schema = json.load(f)

    # Inject the base URI to allow referencing of other schemas in our
    # schema store directory directly
    schema["$id"] = f"file://{schema_store}/"

    # Return the schema and memoize it for later requests of the same schema
    return schema
