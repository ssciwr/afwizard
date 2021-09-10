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


@pytest.fixture
def dataset():
    return adaptivefiltering.DataSet(filename="data/500k_NZ20_Westport.laz")


@pytest.fixture
def minimal_dataset():
    return adaptivefiltering.DataSet(filename="data/minimal.las", georeferenced=False)
