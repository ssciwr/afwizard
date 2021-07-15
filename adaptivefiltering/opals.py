from adaptivefiltering.filter import Filter
from adaptivefiltering.utils import AdaptiveFilteringError


import os
import sys


_opals = None
_opals_directory = None


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


def instantiate_opals_module(name):
    """Instantiate an OPALS module

    This function manages the import and instantiation of an OPALS module. It is delayed
    to allow users to dynamically set the path to their OPALS installation using
    :func:`~adaptivefiltering.set_opals_directory`. Alternatively, it can be
    specified through the environment variable :code:`OPALS_DIR`.

    :param name:
        The name of the OPALS module that we want to load. Note that this
        name is case-sensitive and should match the module name from the
        OPALS documentation.
    :type name: str
    """
    # If we did not yet import the opals package, we do so now
    global _opals
    if _opals is None:
        # Find the OPALS directory specified by the user
        dir = _opals_directory
        if dir is None:
            dir = os.environ.get("OPALS_DIR", None)

        # If we could not find it so far, we error out
        if dir is None:
            raise AdaptiveFilteringError(
                "OPALS directory not set! Use environment variable OPALS_DIR or set_opals_directory"
            )

        # Add the given OPALS directory and its opals subdirectory
        # to the PYTHONPATH. This allows us to do 'import opals' and
        # to import other modules directly from the *.so files
        sys.path.append(dir)
        sys.path.append(os.path.join(dir, "opals"))

        # And programmatically load the module
        _opals = __import__("opals")

    # Import the requested module and instantiate the module class
    python_module = __import__(name)
    opals_module = getattr(python_module, name)
    return opals_module()


class OPALSFilter(Filter, identifier="OPALS", backend=True):
    """A filter implementation based on OPALS"""

    pass
