from adaptivefiltering.dataset import *
from adaptivefiltering.paths import get_temporary_filename
from adaptivefiltering.segmentation import Segment
from adaptivefiltering.asprs import asprs

from . import dataset, minimal_dataset

import io
import numpy as np
import os
import pytest


def test_show_points(dataset):
    # Test visualization - this is not actually very good in the absence of a display
    # But it helps in measuring coverage of the test suite.
    dataset.show_points()

    # The given Dataset has more than 500 points, this a ValueError is raised.
    with pytest.raises(ValueError):
        dataset.show_points(threshold=500)


def test_show_mesh(dataset):
    # test different methods of calling show_mesh
    # generate_geoTif is automatically tested as well
    dataset.show_mesh()
    dataset.show_mesh(resolution=5)
    dataset.show_mesh(
        resolution=5,
    )
    dataset.show_mesh(classification=asprs[5])
    dataset.show_mesh(resolution=3.1, classification=asprs["low_point"])


def test_show_hillshade(dataset):
    dataset.show_hillshade()
    dataset.show_hillshade(resolution=5)
    dataset.show_hillshade(classification=asprs[5])
    dataset.show_hillshade(resolution=3.1, classification=asprs["low_point"])


def test_show_slope(dataset):
    # test different methods of calling show_mesh
    # generate_geoTif is automatically tested as well
    dataset.show_slope()
    dataset.show_slope(resolution=5)
    dataset.show_slope(classification=asprs[5])
    dataset.show_slope(resolution=3.1, classification=asprs["low_point"])


def test_restriction(dataset):
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


def test_restrict(dataset):
    # not really sure how to test this one.
    dataset.restrict()


def test_convert_georef(dataset):
    dataset.convert_georef("EPSG:25832")
