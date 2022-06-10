import click
import contextlib
import functools
import glob
import hashlib
import json
import os
import platform
import requests
import shutil
import tarfile
import tempfile
import uuid
import xdg

from afwizard.utils import AFwizardError

# Storage for the temporary workspace directory
_tmp_dir = None

# Storage for the data directory that will be used to resolve relative paths
_data_dir = None

# The current data archive URL
TEST_DATA_ARCHIVE = "https://github.com/ssciwr/afwizard-test-data/releases/download/2022-06-09/data.tar.gz"
TEST_DATA_CHECKSUM = "fae90a3cf758e2346b81fa0e3b005f2914d059ca182202a1de8f627b1ec0c160"


def set_data_directory(directory, create_dir=False):
    """Set a custom root directory to locate data files

    :param directory:
        The name of the custom data directory.
    :type directory: str
    :param create_dir:
        Whether AFwizard should create the directory if it does
        not already exist.
    :type created_dir: bool
    """

    # Check existence of the given data directory
    if not os.path.exists(directory):
        if create_dir:
            os.makedirs(directory, exist_ok=True)
        else:
            raise FileNotFoundError(
                f"The given data directory '{directory}' does not exist (Use create_dir=True to automatically create it)!"
            )

    # Update the module variable
    global _data_dir
    _data_dir = directory


def get_temporary_workspace():
    """Return a temporary directory that persists across the session

    This should be used as the working directory of any filter workflows
    or other operations that might produce spurious file outputs.
    """
    global _tmp_dir
    if _tmp_dir is None:
        _tmp_dir = tempfile.TemporaryDirectory()

    return _tmp_dir.name


@contextlib.contextmanager
def within_temporary_workspace():
    """A context manager that changes the current working directory to a temporary workspace"""
    old_cwd = os.getcwd()
    os.chdir(get_temporary_workspace())

    yield

    os.chdir(old_cwd)


def get_temporary_filename(extension=""):
    """Create a filename for a temporary file

    Note, the file is not generated, but only a random filename is generated
    and it is ensured, that its directory is correctly created.

    :param extension:
        A file extension that should be appended to the generated filename.
    :type extension: str
    """
    return os.path.join(get_temporary_workspace(), f"{uuid.uuid4()}.{extension}")


def download_test_file(filename):
    """Ensure the existence of a dataset file by downloading it"""

    # We download test data to the temporary workspce
    testdata_dir = os.path.join(get_temporary_workspace(), "data")

    # If we have not done that already, we do so now
    if not os.path.exists(testdata_dir):
        archive = requests.get(TEST_DATA_ARCHIVE).content
        checksum = hashlib.sha256(archive).hexdigest()
        if checksum != TEST_DATA_CHECKSUM:
            raise ValueError("Checksum for test data archive failed.")

        archive_file = os.path.join(get_temporary_workspace(), "data.tar.gz")
        with open(archive_file, "wb") as tar:
            tar.write(archive)

        with tarfile.open(archive_file, "r:gz") as tar:
            tar.extractall(path=testdata_dir)

    # Return the filename - it is only a candidate. If the given filename
    # is not in the test data, the file will not exist.
    return os.path.join(testdata_dir, filename)


def check_file_extension(filename, possible_values, default_value):
    name, ext = os.path.splitext(filename)

    if ext == "" or ext == ".":
        ext = default_value
    possible_extensions = [possible_ext.lower() for possible_ext in possible_values]
    if ext.lower() not in possible_extensions:
        raise AFwizardError(
            f"The file extension {ext} is not supported. Please use the following: {possible_extensions}"
        )
    return os.path.join(name + ext)


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

    # Use the test data directory
    candidates.append(download_test_file(filename))

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


@click.command()
@click.argument(
    "target",
    type=click.Path(exists=True, file_okay=False, writable=True),
    default=os.getcwd(),
)
def copy_notebooks(target):
    """Copy example notebooks into the TARGET directory"""

    # Locate notebook files in the installation tree
    jupyter_dir = os.path.join(os.path.split(__file__)[0], "jupyter")
    notebooks = glob.glob(os.path.join(jupyter_dir, "*.ipynb"))

    # Print a verbose message
    click.echo(f"Copying {len(notebooks)} Jupyter notebooks into directory '{target}'")

    # Do the actual copying
    for notebook in notebooks:
        shutil.copy(notebook, target)
