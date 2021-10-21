# Make sure to import modules that register filter backends
import adaptivefiltering.lastools
import adaptivefiltering.opals
import adaptivefiltering.pdal

# Import those functions and objects that we consider the package user API
from adaptivefiltering.apps import pipeline_tuning
from adaptivefiltering.asprs import asprs
from adaptivefiltering.dataset import DataSet, remove_classification, reproject_dataset
from adaptivefiltering.filter import load_filter, save_filter
from adaptivefiltering.lastools import set_lastools_directory
from adaptivefiltering.opals import set_opals_directory
from adaptivefiltering.paths import set_data_directory
from adaptivefiltering.version import __version__, print_version

# This is necessary for autodoc to generate the User API
# The order of objects in this list defines the order in
# the Sphinx documentation.
__all__ = [
    "DataSet",
    "pipeline_tuning",
    "remove_classification",
    "reproject_dataset",
    "load_filter",
    "save_filter",
    "set_data_directory",
    "set_lastools_directory",
    "set_opals_directory",
    "asprs",
    "print_version",
]
