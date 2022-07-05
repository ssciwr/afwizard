from afwizard.apps import *
from afwizard.filter import load_filter

import dataclasses
import ipywidgets
import os
import pytest


@dataclasses.dataclass
class Obj:
    data: str


def test_return_proxy():
    # Create a proxy for a widget state
    w = ipywidgets.Text()
    proxy = return_proxy(lambda: Obj(w.value), [w])
    assert proxy.data == ""

    # Update the widget and observe changes of the proxy
    w.value = "Foo"
    assert proxy.data == "Foo"


def test_expand_variability():
    assert tuple(expand_variability_string("foo, bar")) == ("foo", "bar")
    assert tuple(expand_variability_string("  foo,bar")) == ("foo", "bar")
    assert tuple(expand_variability_string("1,2,3")) == ("1", "2", "3")
    assert tuple(expand_variability_string("1:2")) == ("1:2",)
    assert tuple(expand_variability_string("1:2", type_="integer")) == (1, 2)
    assert tuple(expand_variability_string("1:2", type_="number")) == (
        1.0,
        1.25,
        1.5,
        1.75,
        2.0,
    )
    assert tuple(expand_variability_string("1:2,5", type_="number")) == (
        1.0,
        1.25,
        1.5,
        1.75,
        2.0,
        5,
    )
    assert tuple(expand_variability_string("1:5:2", type_="integer")) == (1, 3, 5)

    for var, truth in zip(
        expand_variability_string("1:2:0.3", type_="number"), (1.0, 1.3, 1.6, 1.9)
    ):
        assert abs(var - truth) < 1e-8


#
# The following test cases merely instantiate the apps to find bugs in widget
# construction and generate coverage information.
#


def test_pipeline_tuning(minimal_dataset):
    p = pipeline_tuning(datasets=[minimal_dataset])
    p = pipeline_tuning(datasets=[minimal_dataset, minimal_dataset])
    p = pipeline_tuning(minimal_dataset, pipeline=p)


def test_show_interactive(minimal_dataset):
    show_interactive(minimal_dataset)


def test_select_pipeline_from_library(minimal_dataset):
    select_pipeline_from_library()
    select_pipeline_from_library(multiple=True)


def test_select_best_pipeline(minimal_dataset):
    with pytest.raises(AFwizardError):
        select_best_pipeline()

    with pytest.raises(AFwizardError):
        select_best_pipeline(pipelines=[])

    f = load_filter(
        os.path.join(os.path.split(__file__)[0], "library", "myfilter.json")
    )
    select_best_pipeline(dataset=minimal_dataset, pipelines=[f])


def test_execute_interactive(minimal_dataset):
    f = load_filter(
        os.path.join(os.path.split(__file__)[0], "library", "myfilter.json")
    )
    execute_interactive(minimal_dataset, f)
