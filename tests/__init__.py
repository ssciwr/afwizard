import adaptivefiltering
import contextlib
import os
import pytest


@contextlib.contextmanager
def mock_environment(**env):
    """Temporarily update the environment. Implementation taken from
    https://stackoverflow.com/questions/2059482/python-temporarily-modify-the-current-processs-environment/34333710
    """
    old_env = dict(os.environ)
    os.environ.update(env)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def _dataset_fixture(filename, spatial_reference=None):
    @pytest.fixture
    def _fixture():
        return adaptivefiltering.DataSet(filename, spatial_reference=spatial_reference)

    return _fixture


# Fixtures for the provided datasets
dataset = _dataset_fixture("500k_NZ20_Westport.laz")
minimal_dataset = _dataset_fixture("minimal.las", spatial_reference="EPSG:4362")
