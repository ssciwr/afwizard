from afwizard.dataset import DataSet
from afwizard.filter import Filter
from afwizard.paths import (
    get_temporary_filename,
    load_schema,
    within_temporary_workspace,
)
from afwizard.utils import AFwizardError, stringify_parameters

import logging
import os
import platform
import shutil
import subprocess

logger = logging.getLogger("afwizard")

# The module wide storage for the lasground prefix
_lastools_directory = None


def set_lastools_directory(dir):
    """Set custom LASTools installation directory

    Use this function at the beginning of your code to point AFwizard
    to a custom LASTools installation directory. Alternatively, you can use the
    environment variable :code:`LASTOOLS_DIR` to do so.

    :param dir:
        The LASTools installation directory to use
    :type dir: str
    """
    # Globally store the given path
    global _lastools_directory
    _lastools_directory = dir

    # Validate the given directory if it is not None
    if dir is not None:
        try:
            # If this throws, we show a meaningful error where we looked for LASTools
            lasground_executable(base=dir)
        except AFwizardError as e:
            _lastools_directory = None
            raise e


def get_lastools_directory():
    """Find the LASTools directory specified by the user"""
    global _lastools_directory

    # Maybe set the directory from an environment variable
    if _lastools_directory is None:
        dir = os.environ.get("LASTOOLS_DIR", None)
        if dir is not None:
            set_lastools_directory(dir)

    return _lastools_directory


def lastools_is_present():
    """Whether LASTools is present on the system"""
    if platform.system() in ["Linux", "Darwin"]:
        # On Unix, we need to assert that we have Wine to use the
        # Windows-only binaries provided for LASTools
        if shutil.which("wine") is None:
            return False

    # We return True iff a prefix was set
    return get_lastools_directory() is not None


def lasground_executable(base=None):
    """The full path to the lasground executable"""
    if base is None:
        base = get_lastools_directory()

    # Determine the name of the executable (32 vs. 64 Bit)
    execname = "lasground_new.exe"
    if platform.architecture()[0] == "64bit":
        execname = "lasground_new64.exe"

    fullpath = os.path.join(base, "bin", execname)
    if not os.path.exists(fullpath):
        raise AFwizardError(f"Executable {fullpath} was not found!")

    return fullpath


class LASToolsFilter(Filter, identifier="lastools", backend=True):
    def execute(self, dataset, **variability_data):
        # Apply variabilility without changing self
        config = self._modify_filter_config(variability_data)

        # The lasground executable operates on raw LAS/LAZ input
        dataset = DataSet.convert(dataset)

        # Maybe add wine to the command line to execute
        executable = []
        if platform.system() in ["Linux", "Darwin"]:
            executable.append(shutil.which("wine"))

        # Add the full path to the lasground_new executable
        executable.append(lasground_executable())

        # Build the argument list
        args = []
        for k, v in config.items():
            if v != "":
                args.append(f"-{k}")
                args.extend(stringify_parameters(v))

        # Create a filename for lasground output
        outfile = get_temporary_filename(extension="las")

        # Add input and output to the command line
        args.extend(["-i", dataset.filename, "-o", outfile])

        # Call the executable
        with within_temporary_workspace():
            logger.info(
                f"Executing LASTools command line '{' '.join(executable + args)}'"
            )
            result = subprocess.run(
                executable + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

        if result.returncode != 0:
            raise AFwizardError(f"LASTools error: {result.stdout.decode()}")

        return DataSet(
            filename=outfile,
            spatial_reference=dataset.spatial_reference,
        )

    @classmethod
    def enabled(cls):
        return lastools_is_present()

    @classmethod
    def schema(cls):
        return load_schema("lastools.json")
