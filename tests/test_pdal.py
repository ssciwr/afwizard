from adaptivefiltering import DataSet
from adaptivefiltering.pdal import *

import jsonschema
import os
import pyrsistent
import pytest


_pdal_filter_list = [
    "filters.csf",
    "filters.elm",
    "filters.outlier",
    "filters.pmf",
    "filters.skewnessbalancing",
    "filters.smrf",
]


def test_pdal_filter():
    # A configuration without type is not a valid PDAL filter
    with pytest.raises(jsonschema.ValidationError):
        PDALFilter()

    # Instantiate a filter for testing
    f = PDALFilter(type="filters.smrf")

    # Make sure that the filter widget can be displayed
    widget = f.widget_form()

    # And that the filter can be reconstructed using the form data
    f2 = f.copy(**pyrsistent.thaw(widget.data))


def test_pdal_pipeline():
    f = PDALFilter(type="filters.smrf")
    p = f.as_pipeline()

    widget = p.widget_form()
    p2 = p.copy(**pyrsistent.thaw(widget.data))


@pytest.mark.parametrize("f", _pdal_filter_list)
def test_filter_default_settings(f, tmp_path):
    # We run this test from within a temporary directory.
    # This is better because some PDAL filter produce spurious
    # intermediate files.
    os.chdir(tmp_path)

    # Create a dummy data set
    dataset = DataSet(
        filename="data/500k_NZ20_Westport.laz",
    )

    # And execute the filter in default configuration on it
    filter_ = PDALFilter(type=f)
    dataset = filter_.execute(dataset)
