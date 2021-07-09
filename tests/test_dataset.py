import adaptivefiltering
import pytest


def test_adaptivefiltering():
    # Load a dataset
    dataset = adaptivefiltering.DataSet("data/500k_NZ20_Westport.laz")

    # Test visualization - this is not actually very good in the absence of a display
    # But it helps in measuring coverage of the test suite.
    dataset.show()


def test_adaptivefiltering_threshold():
    # Load a dataset and set threshold to 500
    dataset = adaptivefiltering.DataSet("data/500k_NZ20_Westport.laz", 500)
    # The given Dataset has more than 500 points, this a ValueError is raised.
    with pytest.raises(ValueError):
        dataset.show()


def test_adaptivefiltering_show_mesh():
    # Load a dataset
    dataset = adaptivefiltering.DataSet("data/500k_NZ20_Westport.laz")

    # test different methods of calling show_mesh
    # generate_geoTif is automatically tested as well
    dataset.show_mesh()
    dataset.show_mesh(resolution=5)
