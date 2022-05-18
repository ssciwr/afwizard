from afwizard.pdal import *
from afwizard.paths import get_temporary_filename

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
def test_minimal_filter_default_settings(f, tmp_path, minimal_dataset):
    # We run this test from within a temporary directory.
    # This is better because some PDAL filter produce spurious
    # intermediate files.
    os.chdir(tmp_path)

    # And execute the filter in default configuration on it
    filter_ = PDALFilter(type=f)
    dataset = filter_.execute(minimal_dataset)

    form = filter_.widget_form()
    filter_ = filter_.copy(**form.data)
    dataset = filter_.execute(minimal_dataset)

    # Treating the filter as a pipeline should work as well
    pipeline = filter_.as_pipeline()
    dataset = pipeline.execute(minimal_dataset)

    # Do the same on a pipeline that was constructed from a widget
    form = pipeline.widget_form()
    pipeline = pipeline.copy(**form.data)
    dataset = pipeline.execute(minimal_dataset)


@pytest.mark.slow
@pytest.mark.parametrize("f", _pdal_filter_list)
def test_filter_default_settings(f, tmp_path, dataset):
    # We run this test from within a temporary directory.
    # This is better because some PDAL filter produce spurious
    # intermediate files.
    os.chdir(tmp_path)

    # And execute the filter in default configuration on it
    filter_ = PDALFilter(type=f)
    dataset = filter_.execute(dataset)


def test_pdal_inmemory_dataset(minimal_dataset):
    # Check conversion
    dataset = PDALInMemoryDataSet.convert(minimal_dataset)
    assert dataset.data is not None

    # Check idempotency
    dataset2 = PDALInMemoryDataSet.convert(dataset)
    assert dataset2.data.shape == dataset.data.shape

    # Dataset saving and reloading as LAS
    saved = dataset.save(get_temporary_filename("las"))
    reloaded = PDALInMemoryDataSet.convert(saved)
    assert dataset.data.shape == reloaded.data.shape

    # Dataset saving and reloading as LAZ
    saved = dataset.save(get_temporary_filename("laz"))
    reloaded = PDALInMemoryDataSet.convert(saved)
    assert dataset.data.shape == reloaded.data.shape
