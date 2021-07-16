from adaptivefiltering.dataset import DataSet
from adaptivefiltering.filter import Filter
from adaptivefiltering.paths import get_temporary_filename
from adaptivefiltering.utils import AdaptiveFilteringError

import functools
import os
import re
import subprocess
import xmltodict


_opals_directory = None


_availableOpalsModules = [
    "Cell",
    "Grid",
    "RobFilter",
]


def set_opals_directory(dir):
    """Set custom OPALS installation directory

    Use this function at the beginning of your code to point adaptivefiltering
    to a custom OPALS installation directory. Alternatively, you can use the
    environment variable :code:`OPALS_DIR` to do so.

    :param dir:
        The OPALS installation directory to use
    :type dir: str
    """
    global _opals_directory
    _opals_directory = dir


def get_opals_directory():
    """Find the OPALS directory specified by the user"""
    dir = _opals_directory
    if dir is None:
        dir = os.environ.get("OPALS_DIR", None)
    return dir


def opals_is_present():
    """Whether OPALS is present on the system"""
    dir = get_opals_directory()
    return dir is not None


def get_opals_module_executable(module):
    """Find an OPALS executable by inspecting the OPALS installation

    :param module:
        The name of the OPALS module that we want to use. Note that this
        name is case-sensitive and should match the module name from the
        OPALS documentation.
    :type name: str
    """
    base = get_opals_directory()
    if base is None:
        raise AdaptiveFilteringError("OPALS not found")

    # Construct the path and double-check its existence
    path = os.path.join(get_opals_directory(), "opals", f"opals{module}")
    if not os.path.exists(path):
        raise AdaptiveFilteringError("Executable f{path} not found!")

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


def _xmlparam_to_jsonschema(xmldoc, modname, blacklist=[]):
    """Transform an OPALS XML module specification to a JSON schema"""
    result = {"type": "object", "title": f"{modname} Module (OPALS)"}
    props = {}
    required = []
    for param in xmldoc["Parameters"]["Specific"]["Parameter"]:
        # Extract the name and add a corresponding dictionary
        name = param["@Name"]

        # If this parameter name was blacklisted, we skip it
        if name in blacklist:
            continue
        else:
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
    result["properties"]["type"] = {"type": "string", "const": modname}

    # Add required fields
    required.append("type")
    result["required"] = required

    return result


@functools.lru_cache
def assemble_opals_schema():
    """Assemble the schema for all OPALS filters"""
    result = {"anyOf": [], "title": "OPALS Filter"}

    for mod in _availableOpalsModules:
        xmloutput = subprocess.run(
            [
                get_opals_module_executable(mod),
                "--options",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        xmldoc = xmltodict.parse(xmloutput.stderr)
        result["anyOf"].append(
            _xmlparam_to_jsonschema(
                xmldoc, mod, blacklist=["oFormat", "outFile", "debugOutFile", "inFile"]
            )
        )

    return result


def execute_opals_module(dataset=None, config=None, outputfile=None):
    # Create the command line
    module = config.pop("type")
    executable = get_opals_module_executable(module)
    fileargs = ["-inFile", dataset.filename]
    if outputfile:
        fileargs.extend(["-outFile", outputfile])
    args = sum(([f"--{k}", v] for k, v in config.items()), [])

    # Execute the module
    result = subprocess.run([executable] + fileargs + args)


class OPALSFilter(Filter, identifier="OPALS", backend=True):
    """A filter implementation based on OPALS"""

    def execute(self, dataset):
        dataset = OPALSDataManagerObject.convert(dataset)
        outputfile = get_temporary_filename(extension="odm")
        execute_opals_module(dataset=dataset, config=self.config, outputfile=outputfile)
        return OPALSDataManagerObject(
            filename=outputfile,
            provenance=dataset._provenance
            + [
                f"Applying OPALS module with the following configuration: {self._serialize()}"
            ],
        )

    @classmethod
    def schema(cls):
        return assemble_opals_schema()

    @classmethod
    def enabled(cls):
        return opals_is_present()


class OPALSDataManagerObject(DataSet):
    @classmethod
    def convert(cls, dataset):
        # Idempotency of the conversion
        if isinstance(dataset, OPALSDataManagerObject):
            return dataset

        # Construct the new ODM filename
        dm_filename = get_temporary_filename(extension="odm")

        # Run the opalsImport utility
        subprocess.run(
            [
                get_opals_module_executable("Import"),
                "-inFile",
                dataset.filename,
                "-outFile",
                dm_filename,
            ]
        )

        # Wrap the result in a new data set object
        return OPALSDataManagerObject(
            filename=dm_filename, provenance=dataset.provenance
        )
