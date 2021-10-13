from adaptivefiltering.dataset import DataSet
from adaptivefiltering.filter import Filter
from adaptivefiltering.paths import get_temporary_filename, load_schema
from adaptivefiltering.utils import stringify_value

import os
import platform
import shutil
import subprocess


# The module wide storage for the lasground prefix
_lastools_directory = None


def set_lastools_directory(dir):
    """Set custom LASTools installation directory

    Use this function at the beginning of your code to point adaptivefiltering
    to a custom LASTools installation directory. Alternatively, you can use the
    environment variable :code:`LASTOOLS_DIR` to do so.

    :param dir:
        The LASTools installation directory to use
    :type dir: str
    """
    global _lastools_directory
    _lastools_directory = dir


def get_lastools_directory():
    """Find the LASTools directory specified by the user"""
    dir = _lastools_directory
    if dir is None:
        dir = os.environ.get("LASTOOLS_DIR", None)
    return dir


def lastools_is_present():
    """Whether LASTools is present on the system"""
    if platform.system() in ["Linux", "Darwin"]:
        # On Unix, we need to assert that we have Wine to use the
        # Windows-only binaries provided for LASTools
        if shutil.which("wine") is None:
            return False

    # We return True iff a prefix was set
    return get_lastools_directory() is not None


def execute_lasground(config):
    # Determine the name of the executable (32 vs. 64 Bit)
    execname = "lasground_new.exe"
    if platform.architecture()[0] == "64bit":
        execname = "lasground_new64.exe"

    # Maybe add wine to the command line to execute
    executable = []
    if platform.system() in ["Linux", "Darwin"]:
        executable.append(shutil.which("wine"))

    # Add the full path to the lasground_new executable
    executable.append(os.path.join(get_lastools_directory(), "bin", execname))

    # Build the argument list
    args = []
    for k, v in config.items():
        strv = stringify_value(v)
        if strv != "":
            args.append(f"-{k}")
            args.append(strv)

    # Call the executable
    subprocess.run(executable)


class LASToolsFilter(Filter, identifier="lastools", backend=True):
    def execute(self, dataset):
        # The lasground executable operates on raw LAS/LAZ input
        dataset = DataSet.convert(dataset)

        # Determine the name of the executable (32 vs. 64 Bit)
        execname = "lasground_new.exe"
        if platform.architecture()[0] == "64bit":
            execname = "lasground_new64.exe"

        # Maybe add wine to the command line to execute
        executable = []
        if platform.system() in ["Linux", "Darwin"]:
            executable.append(shutil.which("wine"))

        # Add the full path to the lasground_new executable
        executable.append(os.path.join(get_lastools_directory(), "bin", execname))

        # Build the argument list
        args = []
        for k, v in self.config.items():
            strv = stringify_value(v)
            if strv != "":
                args.append(f"-{k}")
                args.append(strv)

        # Create a filename for lasground output
        outfile = get_temporary_filename(extension="las")

        # Add input and output to the command line
        args.extend(["-i", dataset.filename, "-o", outfile])

        # Call the executable
        subprocess.run(executable + args)

        return DataSet(
            filename=outfile,
            provenance=dataset._provenance + [f"Applied LASGround filter"],
            georeferenced=dataset.georeferenced,
        )

    @classmethod
    def enabled(cls):
        return lastools_is_present()

    @classmethod
    def schema(cls):
        return load_schema("lastools.json")

    @classmethod
    def form_schema(cls):
        schema = cls.schema()
        for subschema in schema.get("anyOf", []):
            newprops = {}
            for param, val in subschema.get("properties").items():
                if param not in ["i", "o"]:
                    newprops[param] = val
            subschema["properties"] = newprops

        return schema
