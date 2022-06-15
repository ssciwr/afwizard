# This is the single source of truth
__version__ = "1.0.0b7"

# Ensure inclusion of the logging configuration
import afwizard.logger

# Make sure to import modules that register filter backends
import afwizard.lastools
import afwizard.opals
import afwizard.pdal

# Import those functions and objects that we consider the package user API
from afwizard.apps import (
    execute_interactive,
    pipeline_tuning,
    select_pipeline_from_library,
    select_pipelines_from_library,
    select_best_pipeline,
    assign_pipeline,
)
from afwizard.dataset import DataSet, remove_classification, reproject_dataset
from afwizard.execute import apply_adaptive_pipeline
from afwizard.filter import load_filter, save_filter
from afwizard.lastools import set_lastools_directory
from afwizard.library import (
    add_filter_library,
    reset_filter_libraries,
    set_current_filter_library,
)
from afwizard.opals import set_opals_directory
from afwizard.paths import set_data_directory
from afwizard.segmentation import load_segmentation


def print_version():
    """Print the current version of AFwizard"""
    print(__version__)


# This is necessary for autodoc to generate the User API
# The order of objects in this list defines the order in
# the Sphinx documentation.
__all__ = [
    "DataSet",
    "pipeline_tuning",
    "select_best_pipeline",
    "select_pipeline_from_library",
    "select_pipelines_from_library",
    "assign_pipeline",
    "apply_adaptive_pipeline",
    "execute_interactive",
    "remove_classification",
    "reproject_dataset",
    "load_segmentation",
    "load_filter",
    "save_filter",
    "set_current_filter_library",
    "set_data_directory",
    "set_lastools_directory",
    "set_opals_directory",
    "add_filter_library",
    "reset_filter_libraries",
    "print_version",
]
