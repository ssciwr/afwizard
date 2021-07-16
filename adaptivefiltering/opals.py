from adaptivefiltering.filter import Filter
from adaptivefiltering.paths import load_schema
from adaptivefiltering.utils import AdaptiveFilteringError

import functools
import os
import re
import subprocess
import sys
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


def get_opals_module_executable(module):
    """Find an OPALS executable by inspecting the OPALS installation

    :param module:
        The name of the OPALS module that we want to use. Note that this
        name is case-sensitive and should match the module name from the
        OPALS documentation.
    :type name: str
    """
    # Find the OPALS directory specified by the user
    dir = _opals_directory
    if dir is None:
        dir = os.environ.get("OPALS_DIR", None)

    # If we could not find it so far, we error out
    if dir is None:
        raise AdaptiveFilteringError(
            "OPALS directory not set! Use environment variable OPALS_DIR or set_opals_directory"
        )

    # Construct the path and double-check its existence
    path = os.path.join(dir, "opals", f"opals{module}")
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

    # Maybe add required fields
    if required:
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
            _xmlparam_to_jsonschema(xmldoc, mod, blacklist=["debugOutFile", "inFile"])
        )

    return result


def execute_opals_module(dataset=None, config=None):
    # Create the command line
    module = config.pop("type")
    executable = get_opals_module_executable(module)
    args = sum(([f"--{k}", v] for k, v in config.items()), [])

    # Execute the module
    result = subprocess.run([executable] + args)


class OPALSFilter(Filter, identifier="OPALS", backend=True):
    """A filter implementation based on OPALS"""

    def execute(self, dataset):
        execute_opals_module(dataset=dataset, config=self.config)

    @classmethod
    def schema(cls):
        return assemble_opals_schema()
