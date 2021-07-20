from adaptivefiltering.dataset import *
from adaptivefiltering.segmentation import Segment

from . import dataset

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


def test_restriction(dataset):
    segment = Segment([[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]])
    restricted = dataset.restrict(segment)


def test_dataset_interoperability(dataset):
    pass
