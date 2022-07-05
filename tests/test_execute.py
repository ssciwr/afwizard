from afwizard.dataset import DataSet
from afwizard.execute import *
from afwizard.filter import load_filter
from afwizard.library import add_filter_library, metadata_hash
from afwizard.paths import get_temporary_workspace
from afwizard.pdal import PDALInMemoryDataSet
from afwizard.utils import AFwizardError

import os
import pytest


def test_apply_adaptive_pipeline(dataset, dataset_seg, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    # Apply without pipeline information in segmentation
    with pytest.raises(AFwizardError):
        apply_adaptive_pipeline(dataset=dataset, segmentation=dataset_seg)

    # Register the test data filter library
    add_filter_library(os.path.join(get_temporary_workspace(), "data"))

    # Patch pipeline information into the segementation
    for s in dataset_seg["features"]:
        mapping = {
            "A": "testfilter1.json",
            "B": "testfilter2.json",
            "C": "testfilter2.json",
            "D": "testfilter1.json",
        }
        s["properties"]["pipeline"] = metadata_hash(
            load_filter(mapping[s["properties"]["class"]])
        )

    # Now do a proper apply
    apply_adaptive_pipeline(dataset=dataset, segmentation=dataset_seg)

    # Assert existence of output files
    lasoutput = os.path.join(
        os.path.join(tmp_path, "output", "500k_NZ20_Westport_filtered.las")
    )
    tiffoutput = os.path.join(
        os.path.join(tmp_path, "output", "500k_NZ20_Westport_filtered.tiff")
    )

    assert os.path.exists(lasoutput) is True
    assert os.path.exists(tiffoutput) is True

    # Assert that the generated dataset is readable
    ds = DataSet(lasoutput)
    ds = PDALInMemoryDataSet.convert(ds)
    assert ds.data.shape[0] > 0
