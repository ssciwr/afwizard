from afwizard.filter import *
from afwizard.pdal import PDALFilter

import pytest


# A list of simple no-op filters for test parametrization
filters = [PDALFilter(type="filters.smrf")]
pipelines = [filters[0] + filters[0], filters[0].as_pipeline()]


def test_baseclass_conversions():
    # An example filter
    f = PDALFilter(type="filters.smrf")

    # Create a pipeline from the filter
    pipeline = f.as_pipeline()
    assert isinstance(pipeline, PipelineMixin)
    assert len(pipeline.config["filters"]) == 1

    # Filter creation is idempotent
    pipeline = pipeline.as_pipeline()
    assert isinstance(pipeline, PipelineMixin)
    assert len(pipeline.config["filters"]) == 1

    # Test addition operators
    def test_add(a, b):
        add = a + b
        assert isinstance(add, PipelineMixin)
        assert len(add.config["filters"]) == 2

    # Test all combinations of types for operator +
    test_add(f, f)
    test_add(pipeline, f)
    test_add(f, pipeline)
    test_add(pipeline, pipeline)

    # operator += is not available for filters
    def unavailable_iadd(a, b):
        with pytest.raises(FilterError):
            a += b

    # Against test all combinations
    unavailable_iadd(f, f)
    unavailable_iadd(f, pipeline)

    # Test operator += for pipelines
    def test_iadd(a, b):
        a2 = a.copy()
        a2 += b
        assert isinstance(a2, PipelineMixin)
        assert len(a2.config["filters"]) == 2

    # Combinations
    test_iadd(pipeline, f)
    test_iadd(pipeline, pipeline)


def test_custom_filter_backend():
    # Incorrect backend that does not register with the base class
    with pytest.raises(FilterError):

        class CustomBackend(Filter):
            pass

    # or uses a name already taken
    with pytest.raises(FilterError):

        class CustomBackend(Filter, identifier="pdal"):
            pass


@pytest.mark.parametrize("f", filters + pipelines)
def test_serialization(f, tmp_path):
    # Test pure serialization
    f2 = deserialize_filter(serialize_filter(f))
    assert f.config == f2.config
    assert type(f) == type(f2)

    # Test file saving and loading
    filename = os.path.join(tmp_path, "test.json")
    save_filter(f, filename)
    f2 = load_filter(filename)
    assert f.config == f2.config
    assert type(f) == type(f2)


@pytest.mark.parametrize("p", pipelines)
def test_pipeline(p):
    author = "Dominic Kempf"
    description = "This is a test pipeline with metadata"
    example_data_url = "https://github.com/ssciwr"

    p = p.copy(
        metadata=dict(
            author=author, description=description, example_data_url=example_data_url
        )
    )

    assert p.author == author
    assert p.description == description
    assert p.example_data_url == example_data_url

    form = p.widget_form()
    p2 = p.copy(**form.data)
