from adaptivefiltering.filter import *
from adaptivefiltering.pdal import PDALFilter

import jsonschema
import pytest


def test_pdal_filter():
    # Filters cannot be constructed without a configuration
    with pytest.raises(FilterError):
        PDALFilter()

    # An empty configuration is not a valid PDAL filter
    with pytest.raises(jsonschema.ValidationError):
        PDALFilter(config={})

    # Instantiate a filter for testing
    f = PDALFilter(config={"type": "filters.crop"})

    # Make sure that the filter widget can be displayed
    widget = f.widget_form()

    # And that the filter can be reconstructed using the form data
    f2 = f.copy(**widget.data())


def test_baseclass_conversions():
    # An example filter
    f = PDALFilter(config={"type": "filters.crop"})

    # Create a pipeline from the filter
    pipeline = f.as_pipeline()
    assert isinstance(pipeline, Pipeline)
    assert len(pipeline.filters) == 1

    # Filter creation is idempotent
    pipeline = pipeline.as_pipeline()
    assert isinstance(pipeline, Pipeline)
    assert len(pipeline.filters) == 1

    # Filters and pipelines can be turned into profiles
    profile = f.as_profile()
    assert isinstance(profile, Profile)
    assert len(profile.filters) == 1
    profile = pipeline.as_profile()
    assert isinstance(profile, Profile)
    assert len(profile.filters) == 1

    # Test addition operators
    def test_add(a, b):
        add = a + b
        assert isinstance(add, Pipeline)
        assert len(add.filters) == 2

    # Test all combinations of types for operator +
    test_add(f, f)
    test_add(pipeline, f)
    test_add(f, pipeline)
    test_add(pipeline, pipeline)
    test_add(profile, f)
    test_add(f, profile)
    test_add(profile, profile)
    test_add(profile, pipeline)
    test_add(pipeline, profile)

    # operator += is not available for filters
    def unavailable_iadd(a, b):
        with pytest.raises(FilterError):
            a += b

    # Against test all combinations
    unavailable_iadd(f, f)
    unavailable_iadd(f, pipeline)
    unavailable_iadd(f, profile)

    # Test operator += for pipelines and profile
    def test_iadd(a, b):
        a2 = a.copy()
        a2 += b
        assert isinstance(a2, Pipeline)
        assert len(a2.filters) == 2

    # Combinations
    test_iadd(pipeline, f)
    test_iadd(pipeline, pipeline)
    test_iadd(pipeline, profile)
    test_iadd(profile, f)
    test_iadd(profile, pipeline)
    test_iadd(profile, profile)


def test_custom_filter_backend():
    # Incorrect backend that does not register with the base class
    with pytest.raises(FilterError):

        class CustomBackend(Filter):
            pass

    # or uses a name already taken
    with pytest.raises(FilterError):

        class CustomBackend(Filter, identifier="pdal"):
            pass


@pytest.mark.parametrize(
    "f", (PDALFilter(config={"type": "filters.crop"}), Filter(config={}))
)
def test_serialization(f, tmp_path):
    # Test pure serialization
    f2 = deserialize_filter(serialize_filter(f))
    assert f.config == f2.config

    # Test file saving and loading
    filename = os.path.join(tmp_path, "test.json")
    save_filter(f, filename)
    f2 = load_filter(filename)
    assert f.config == f2.config


@pytest.mark.parametrize(
    "f", (PDALFilter(config={"type": "filters.crop"}), Filter(config={}))
)
def test_profile(f):
    author = "Dominic Kempf"
    description = "This is a test profile"
    example_data_url = "https://github.com/ssciwr"

    p = f.as_profile(
        author=author, description=description, example_data_url=example_data_url
    )

    assert p.author == author
    assert p.description == description
    assert p.example_data_url == example_data_url
