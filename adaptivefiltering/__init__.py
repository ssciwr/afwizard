# This is the single source of truth
__version__ = "1.0.0b1"

# Ensure inclusion of the logging configuration
import adaptivefiltering.logger

# Make sure to import modules that register filter backends
import adaptivefiltering.lastools
import adaptivefiltering.opals
import adaptivefiltering.pdal

# Import those functions and objects that we consider the package user API
from adaptivefiltering.apps import (
    execute_interactive,
    pipeline_tuning,
    select_pipeline_from_library,
    select_pipelines_from_library,
    select_best_pipeline,
    assign_pipeline,
)
from adaptivefiltering.dataset import DataSet, remove_classification, reproject_dataset
from adaptivefiltering.execute import apply_adaptive_pipeline
from adaptivefiltering.filter import load_filter, save_filter
from adaptivefiltering.lastools import set_lastools_directory
from adaptivefiltering.library import (
    add_filter_library,
    reset_filter_libraries,
    set_current_filter_library,
)
from adaptivefiltering.opals import set_opals_directory
from adaptivefiltering.paths import set_data_directory
from adaptivefiltering.segmentation import load_segmentation


def print_version():
    """Print the current version of adaptivefiltering"""
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
