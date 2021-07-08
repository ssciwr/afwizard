# Make sure to import modules that register filter backends
import adaptivefiltering.pdal

# Import those functions and objects that we consider the package user API
from adaptivefiltering.dataset import DataSet
from adaptivefiltering.filter import load_filter, save_filter
from adaptivefiltering.paths import set_data_directory

# This is necessary for autodoc to generate the User API
# The order of objects in this list defines the order in
# the Sphinx documentation.
__all__ = ["DataSet", "load_filter", "save_filter", "set_data_directory"]
