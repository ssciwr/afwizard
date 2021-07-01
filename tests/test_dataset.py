import adaptivefiltering
import pytest


def test_adaptivefiltering():
    # Load a dataset
    dataset = adaptivefiltering.DataSet("data/500k_NZ20_Westport.laz")

    # Test visualization - this is not actually very good in the absence of a display
    # But it helps in measuring coverage of the test suite.
    dataset.show()


def test_adaptivefiltering_threshold(capfd):
    # Load a dataset and set threshold to 500
    dataset = adaptivefiltering.DataSet("data/500k_NZ20_Westport.laz")
    # The given Dataset has more than 500 points, check if "this is a warning:" is part of the output string.

    dataset.show(warning_threshold=500)
    out, err = capfd.readouterr()
    assert "This is a warning:" in out
