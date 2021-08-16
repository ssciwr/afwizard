from adaptivefiltering.dataset import *
from adaptivefiltering.paths import get_temporary_filename
from adaptivefiltering.segmentation import Segment

from . import dataset, minimal_dataset

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


def test_show_hillshade(dataset):
    dataset.show_hillshade()


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


def test_asprs_classification():
    assert asprs[42] == (42,)
    assert asprs["ground"] == (2,)
    assert asprs[42, 17] == (17, 42)
    assert asprs[42, "ground"] == (2, 42)
    assert asprs["low_vegetation", "ground"] == (2, 3)
    assert asprs["low_vegetation  ", " ground "] == (2, 3)
    assert asprs["low_vegetation,ground"] == (2, 3)
    assert asprs["  low_vegetation ,  ground"] == (2, 3)
    assert asprs[2:4] == (2, 3, 4)
    assert asprs[2:4:2] == (2, 4)
    assert asprs[:4] == (0, 1, 2, 3, 4)
    assert asprs[253:] == (253, 254, 255)

    with pytest.raises(AdaptiveFilteringError):
        asprs["non-existing"]

    with pytest.raises(AdaptiveFilteringError):
        asprs[-1]

    with pytest.raises(AdaptiveFilteringError):
        asprs[256]
