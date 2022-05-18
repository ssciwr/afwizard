from afwizard.filter import save_filter
from afwizard.library import add_filter_library, reset_filter_libraries
from afwizard.pdal import PDALFilter

import afwizard
import json
import os


def test_noop_add(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    reset_filter_libraries()

    # Without a filter or metadata, this should be no-op
    add_filter_library(os.getcwd(), name=None)
    assert len(afwizard.library._filter_libraries) == 2


def test_meta_only_add(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    reset_filter_libraries()

    # Write the metadata file
    metadata = {"name": "Test library"}
    os.makedirs(os.path.join(os.getcwd(), "lib"))
    with open(os.path.join(os.getcwd(), "lib", "library.json"), "w") as f:
        json.dump(metadata, f)

    # This should be recognized although it has 0 filters
    add_filter_library("lib")
    assert len(afwizard.library._filter_libraries) == 3
    assert len(afwizard.library._filter_libraries[2].filters) == 0
    assert afwizard.library._filter_libraries[2].name is not None


def test_filter_only_add(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    reset_filter_libraries()

    # Write a filter to a file
    filter = PDALFilter(type="filters.csf").as_pipeline()
    os.makedirs(os.path.join(os.getcwd(), "lib"))
    save_filter(filter, os.path.join(os.getcwd(), "lib", "myfilter.json"))

    # This should be recognized although it has 0 filters
    add_filter_library(os.path.join(os.getcwd(), "lib"))
    assert len(afwizard.library._filter_libraries) == 3
    assert len(afwizard.library._filter_libraries[2].filters) == 1


def test_nonfilter_json(monkeypatch, tmp_path):
    # Ensure that a JSON file that is not a filter does not make the
    # system fall over
    monkeypatch.chdir(tmp_path)

    with open("something.json", "w") as f:
        json.dump({"bla": 42}, f)

    reset_filter_libraries()
