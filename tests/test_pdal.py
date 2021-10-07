from adaptivefiltering.pdal import *
from adaptivefiltering.paths import get_temporary_filename
from adaptivefiltering import load_filter
from . import dataset, minimal_dataset, example_pipeline

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
def test_minimal_filter_default_settings(f, tmp_path, minimal_dataset, monkeypatch):
    # We run this test from within a temporary directory.
    # This is better because some PDAL filter produce spurious
    # intermediate files.

    monkeypatch.chdir(tmp_path)

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
def test_filter_default_settings(f, tmp_path, dataset, monkeypatch):
    # We run this test from within a temporary directory.
    # This is better because some PDAL filter produce spurious
    # intermediate files.

    monkeypatch.chdir(tmp_path)

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
    saved = dataset.save(get_temporary_filename("laz"), compress=True)
    reloaded = PDALInMemoryDataSet.convert(saved)
    assert dataset.data.shape == reloaded.data.shape


def test_pdal_maintain_metadata(dataset, example_pipeline):
    pdal_dataset = PDALInMemoryDataSet.convert(dataset)
    pdal_dataset_1 = example_pipeline.execute(pdal_dataset)

    assert dataset.spatial_ref["spatial_ref"] is None
    assert pdal_dataset.spatial_ref["spatial_ref"] is not None
    assert "4326" in pdal_dataset.spatial_ref["spatial_ref"]
    assert (
        pdal_dataset_1.spatial_ref["spatial_ref"]
        is pdal_dataset.spatial_ref["spatial_ref"]
    )
