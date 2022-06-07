from afwizard.dataset import DataSet
from afwizard.filter import Filter
from afwizard.paths import (
    get_temporary_filename,
    get_temporary_workspace,
    load_schema,
)
from afwizard.utils import AFwizardError, stringify_parameters

import click
import json
import jsonschema
import logging
import os
import platform
import pyrsistent
import re
import shutil
import subprocess
import xmltodict

logger = logging.getLogger("afwizard")

_opals_directory = None


def set_opals_directory(dir):
    """Set custom OPALS installation directory

    Use this function at the beginning of your code to point AFwizard
    to a custom OPALS installation directory. Alternatively, you can use the
    environment variable :code:`OPALS_DIR` to do so.

    :param dir:
        The OPALS installation directory to use
    :type dir: str
    """
    # Globally store the given path
    global _opals_directory
    _opals_directory = dir

    # Validate the given directory if it is not None
    if dir is not None:
        try:
            get_opals_module_executable("RobFilter", base=dir)
        except AFwizardError:
            _opals_directory = None
            raise AFwizardError(f"Path {dir} does not contain an OPALS installation!")


def get_opals_directory():
    """Find the OPALS directory specified by the user"""
    global _opals_directory

    # Maybe set the directory from an environment variable
    if _opals_directory is None:
        dir = os.environ.get("OPALS_DIR", None)
        if dir is not None:
            set_opals_directory(dir)

    return _opals_directory


def opals_is_present():
    """Whether OPALS is present on the system"""
    dir = get_opals_directory()
    return dir is not None


def get_opals_module_executable(module, base=None):
    """Find an OPALS executable by inspecting the OPALS installation

    :param module:
        The name of the OPALS module that we want to use. Note that this
        name is case-sensitive and should match the module name from the
        OPALS documentation.
    :type name: str
    """

    if base is None:
        base = get_opals_directory()
    if base is None:
        raise AFwizardError("OPALS not found")

    # Construct the path and double-check its existence
    execname = f"opals{module}"

    # On Windows, executables end on .exe
    if platform.system() == "Windows":
        execname = f"{execname}.exe"

    path = os.path.join(get_opals_directory(), "opals", execname)
    if not os.path.exists(path):
        raise AFwizardError(f"Executable {path} not found!")

    return path


def _opals_to_jsonschema_typemapping(_type, schema):
    # Define a mapping of scalar types to their equivalents
    _simple_types = {
        "bool": "boolean",
        "Path": "string",
        "double": "number",
        "float": "number",
        "String": "string",
        "uint32": "integer",
        "int32": "integer",
    }

    # If this is a simple type, we are done
    if _type in _simple_types:
        schema["type"] = _simple_types[_type]
        return

    # This may be a list:
    match = re.match("Vector<(.*)>", _type)
    if match:
        subtype = match.groups()[0]
        schema["type"] = "array"
        schema["items"] = {}
        _opals_to_jsonschema_typemapping(subtype, schema["items"])
        return

    # If we have not identified this type by now, it should be one of OPALS
    # enum types that we are identifying as strings.
    schema["type"] = "string"


@click.command()
@click.argument("mod")
def _automated_opals_schema(mod):
    """Automatically extract the JSON schema for a given module

    This can be used as a great basis to add a new module MOD to AFwizard,
    but it might need some manual adaption to be fully functional.
    """
    xmloutput = subprocess.run(
        [
            get_opals_module_executable(mod),
            "--options",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    xmldoc = xmltodict.parse(xmloutput.stderr)

    # The resulting schema object
    result = {
        "type": "object",
        "title": f"{mod} Module (OPALS)",
        "additionalProperties": False,
    }
    props = {}
    required = []
    for param in xmldoc["Parameters"]["Specific"]["Parameter"]:
        # Extract the name and add a corresponding dictionary
        name = param["@Name"]
        props[name] = {}

        # Map the specified types from OPALS XML to JSON schema
        _opals_to_jsonschema_typemapping(param["@Type"], props[name])

        # Add the title field
        if "@Desc" in param:
            props[name]["title"] = param["@Desc"]

        # Add the description
        if "@LongDesc" in param:
            props[name]["description"] = param["@LongDesc"]

        # Treat the required option. We exclude parameters with a default here,
        # although OPALS marks them as mandatory.
        if param.get("@Opt", "optional") == "mandatory" and "Val" not in param:
            required.append(name)

        # Add the default value
        if "Val" in param:
            # Define a data conversion function depending on the type
            func = lambda x: x
            if param["@Type"] == "bool":
                func = lambda x: eval(x)

            # Set the default applying type conversion
            props[name]["default"] = func(param["Val"])

        # Add a potential enum
        if "Choice" in param:
            props[name]["enum"] = param["Choice"]

    # Add the collected properties
    result["properties"] = props

    # Add the type identifier
    result["properties"]["type"] = {"type": "string", "const": mod}

    # Add required fields

    # TODO: This is currently restricted to "type", because the schemas
    #       exported by OPALS have some inconsistencies.
    required = []

    required.append("type")
    result["required"] = required

    # Print the result on the command line
    print(json.dumps(result))


def execute_opals_module(dataset=None, config=None):
    """Implement execution logic for OPALS modules"""
    # Create the command line
    config = pyrsistent.thaw(config)
    module = config.pop("type")
    executable = get_opals_module_executable(module)
    fileargs = ["-inFile", dataset.filename]

    # Build the argument list
    args = []
    for k, v in config.items():
        if v != "":
            args.append(f"--{k}")
            args.extend(stringify_parameters(v))

    # Execute the module
    logger.info(
        f"Executing OPALS command line '{' '.join([executable] + fileargs + args)}'"
    )
    result = subprocess.run(
        [executable] + fileargs + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=get_temporary_workspace(),
    )

    # If the OPALS run was not successful, we raise an error
    if result.returncode != 0:
        raise AFwizardError(f"OPALS error: {result.stdout.decode()}")


class OPALSFilter(Filter, identifier="opals", backend=True):
    """A filter implementation based on OPALS"""

    def execute(self, dataset, **variability_data):
        """Execution of an OPALS module

        This interfaces with OPALS using its CLI.
        """

        # Make sure that the dataset is available in the OPALS format
        dataset = OPALSDataManagerObject.convert(dataset)

        # Sneak the outFile parameter into the configuration for those filters
        # that require it. For all others, make a copy of the data to prevent
        # any harm from OPALS implicit in-place operation.
        final_filter = self
        outFile = get_temporary_filename(extension="odm")
        try:
            final_filter = self.copy(outFile=outFile)
        except jsonschema.ValidationError:
            shutil.copy(dataset.filename, outFile)
            dataset = OPALSDataManagerObject(
                filename=outFile, spatial_reference=dataset.spatial_reference
            )

        # Apply variabilility without changing filter
        config = final_filter._modify_filter_config(variability_data)

        # Actually run the CLI
        execute_opals_module(dataset=dataset, config=config)

        return OPALSDataManagerObject(
            filename=outFile,
            spatial_reference=dataset.spatial_reference,
        )

    @classmethod
    def schema(cls):
        return load_schema("opals.json")

    @classmethod
    def form_schema(cls):
        schema = cls.schema()
        for subschema in schema.get("anyOf", []):
            newprops = {}
            for param, val in subschema.get("properties").items():
                if param not in ["oFormat", "outFile", "debugOutFile", "inFile"]:
                    newprops[param] = val
            subschema["properties"] = newprops

        return schema

    @classmethod
    def enabled(cls):
        return opals_is_present()


class OPALSNightlyFilter(OPALSFilter, identifier="opals_nightly", backend=True):
    @classmethod
    def schema(cls):
        return load_schema("opals_nightly.json")

    @classmethod
    def enabled(cls):
        # We identify the OPALS nightly installation by the existence
        # of the TerrainFilter module. My OPALS tarball contains an outdated
        # version file, so that cannot be used as a version source
        try:
            get_opals_module_executable("TerrainFilter")
            return True
        except AFwizardError:
            return False


class OPALSDataManagerObject(DataSet):
    @classmethod
    def convert(cls, dataset):
        # Idempotency of the conversion
        if isinstance(dataset, OPALSDataManagerObject):
            return dataset

        # OPALS requires manual specification of the reference system
        if dataset.spatial_reference is None:
            raise AFwizardError(
                "OPALS requires manual setting of the spatial_reference parameter of the DataSet."
            )

        # If dataset is of unknown type, we should first dump it to disk
        dataset = dataset.save(get_temporary_filename("las"))

        # Construct the new ODM filename
        dm_filename = get_temporary_filename(extension="odm")

        # Run the opalsImport utility
        result = subprocess.run(
            [
                get_opals_module_executable("Import"),
                "-inFile",
                dataset.filename,
                "-outFile",
                dm_filename,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        # If the OPALS run was not successful, we raise an error
        if result.returncode != 0:
            raise AFwizardError(f"OPALS error: {result.stdout.decode()}")

        # Wrap the result in a new data set object
        return OPALSDataManagerObject(
            filename=dm_filename,
            spatial_reference=dataset.spatial_reference,
        )

    def save(self, filename, compress=False, overwrite=False):
        # I cannot find LAZ export in the OPALS docs
        if compress:
            raise AFwizardError("OPALS does not implement LAZ exporting")

        # Check if we would overwrite an input file
        if not overwrite and os.path.exists(filename):
            raise AFwizardError(
                f"Would overwrite file '{filename}'. Set overwrite=True to proceed"
            )

        # Run the opalsExport utility
        result = subprocess.run(
            [
                get_opals_module_executable("Export"),
                "-inFile",
                self.filename,
                "-outFile",
                filename,
                "-oFormat",
                "las",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        # If the OPALS run was not successful, we raise an error
        if result.returncode != 0:
            raise AFwizardError(f"OPALS error: {result.stdout.decode()}")

        # Wrap the result in a new data set object
        return DataSet(
            filename=filename,
            spatial_reference=self.spatial_reference,
        )
