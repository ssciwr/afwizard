import adaptivefiltering


def test_adaptivefiltering():
    # Load a dataset
    dataset = adaptivefiltering.DataSet("data/500k_NZ20_Westport.laz")

    # Test visualization - this is not actually very good in the absence of a display
    # But it helps in measuring coverage of the test suite.
    dataset.show()
