# Import those functions and objects that we consider the package user API
from adaptivefiltering.dataset import DataSet
from adaptivefiltering.paths import set_data_directory

# This is necessary for autodoc to generate the User API
# The order of objects in this list defines the order in
# the Sphinx documentation.
__all__ = ["DataSet", "set_data_directory"]
