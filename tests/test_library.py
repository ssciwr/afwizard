from adaptivefiltering.filter import save_filter
from adaptivefiltering.library import add_filter_library, reset_filter_libraries
from adaptivefiltering.pdal import PDALFilter

import adaptivefiltering
import json
import os


def test_noop_add(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    reset_filter_libraries()

    # Without a filter or metadata file, this should be no-op
    add_filter_library(os.getcwd())
    assert len(adaptivefiltering.library._filter_libraries) == 0


def test_meta_only_add(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    reset_filter_libraries()

    # Write the metadata file
    metadata = {"name": "Test library"}
    with open(os.path.join(os.getcwd(), "library.json"), "w") as f:
        json.dump(metadata, f)

    # This should be recognized although it has 0 filters
    add_filter_library(os.getcwd())
    assert len(adaptivefiltering.library._filter_libraries) == 1
    assert len(adaptivefiltering.library._filter_libraries[0].filters) == 0
    assert adaptivefiltering.library._filter_libraries[0].name is not None


def test_filter_only_add(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    reset_filter_libraries()

    # Write a filter to a file
    filter = PDALFilter(type="filters.csf")
    save_filter(filter, os.path.join(os.getcwd(), "myfilter.json"))

    # This should be recognized although it has 0 filters
    add_filter_library(os.getcwd())
    assert len(adaptivefiltering.library._filter_libraries) == 1
    assert len(adaptivefiltering.library._filter_libraries[0].filters) == 1
    assert adaptivefiltering.library._filter_libraries[0].name is None
