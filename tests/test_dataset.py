from adaptivefiltering.dataset import DataSet
from adaptivefiltering.segmentation import Segment

import pytest


def test_adaptivefiltering():
    # Load a dataset
    dataset = DataSet(filename="data/500k_NZ20_Westport.laz")

    # Test visualization - this is not actually very good in the absence of a display
    # But it helps in measuring coverage of the test suite.
    dataset.show_points()


def test_adaptivefiltering_threshold():
    # Load a dataset and set threshold to 500
    dataset = DataSet(
        filename="data/500k_NZ20_Westport.laz",
    )
    # The given Dataset has more than 500 points, this a ValueError is raised.
    with pytest.raises(ValueError):
        dataset.show_points(threshold=500)


def test_adaptivefiltering_show_mesh():
    # Load a dataset
    dataset = DataSet(filename="data/500k_NZ20_Westport.laz")

    # test different methods of calling show_mesh
    # generate_geoTif is automatically tested as well
    dataset.show_mesh()
    dataset.show_mesh(resolution=5)


def test_restriction():
    dataset = DataSet(filename="data/500k_NZ20_Westport.laz")

    segment = Segment([[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]])
    restricted = dataset.restrict(segment)
