from adaptivefiltering.dataset import *
from adaptivefiltering.paths import get_temporary_filename
from adaptivefiltering.segmentation import Segment
from adaptivefiltering.asprs import asprs

from . import dataset, minimal_dataset

import io
import numpy as np
import os
import pytest


def test_show(dataset):
    # Test visualization - this is not actually very good in the absence of a display
    # But it helps in measuring coverage of the test suite.
    dataset.show(visualization_type="hillshade")
    dataset.show(visualization_type="hillshade", resolution=5.0)
    dataset.show(visualization_type="hillshade", classification=asprs[5])
    dataset.show(visualization_type="slopemap")
    dataset.show(visualization_type="slopemap", resolution=5.0)
    dataset.show(visualization_type="slopemap", classification=asprs[5])
    dataset.show(visualization_type="mesh")
    dataset.show(visualization_type="mesh", resolution=5.0)
    dataset.show(visualization_type="mesh", classification=asprs[5])
    dataset.show(visualization_type="scatter")

    # Scatter plots are subject to a point limit
    with pytest.raises(ValueError):
        dataset.show(visualization_type="scatter", threshold=500)


def test_restriction(dataset):
    # Trigger generation of the UI
    dataset.restrict()

    # Programmatically restrict with an artificial segment
    segment = Segment([[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]])
    restricted = dataset.restrict(segment)


def test_save_dataset(minimal_dataset):
    # This should do nothing
    minimal_dataset.save(minimal_dataset.filename)

    # Copy to another file
    tmpfile = get_temporary_filename()
    minimal_dataset.save(tmpfile)
    assert os.stat(tmpfile).st_size == os.stat(minimal_dataset.filename).st_size

    # Try doing that again without the override flag
    with pytest.raises(AdaptiveFilteringError):
        minimal_dataset.save(tmpfile)

    # Now with the override flag
    minimal_dataset.save(tmpfile, overwrite=True)


def test_remove_classification(minimal_dataset):
    removed = remove_classification(minimal_dataset)
    vals = tuple(np.unique(removed.data["Classification"]))
    assert vals == (1,)


def test_provenance(minimal_dataset):
    # For now, only check that output to a stream works
    with io.StringIO() as out:
        minimal_dataset.provenance(out)


def test_reproject_dataset(dataset):
    from adaptivefiltering.dataset import reproject_dataset

    dataset2 = reproject_dataset(dataset, "EPSG:4362")

    # TODO: The following tests fail in CI with "ValueError: Iteration of zero-sized
    #       operands is not enabled" being thrown from PDAL. This is rather obscure.
    # dataset3 = reproject_dataset(dataset2, "EPSG:25833 - ETRS89 / UTM zone 33N")
    # dataset3 = reproject_dataset(
    #     dataset2, "EPSG:25833 - ETRS89 / UTM zone 33N", in_srs="EPSG:4362"
    # )
