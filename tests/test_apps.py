from adaptivefiltering.apps import *

import dataclasses
import ipywidgets


@dataclasses.dataclass
class Obj:
    data: str


def test_return_proxy():
    # Create a proxy for a widget state
    w = ipywidgets.Text()
    proxy = InteractiveWidgetOutputProxy(lambda: Obj(w.value))
    assert proxy.data == ""

    # Update the widget and observe changes of the proxy
    w.value = "Foo"
    assert proxy.data == "Foo"

    # Finalize the proxy
    proxy._finalize()

    # Ensure that changes to the widgets do not change the proxy anymore
    w.value = "Bar"
    assert proxy.data == "Foo"


def test_expand_variability():
    assert tuple(expand_variability_string("foo, bar")) == ("foo", "bar")
    assert tuple(expand_variability_string("  foo,bar")) == ("foo", "bar")
    assert tuple(expand_variability_string("1,2,3")) == ("1", "2", "3")
    assert tuple(expand_variability_string("1-2")) == ("1-2",)
    assert tuple(expand_variability_string("1-2", type_="integer")) == (1, 2)
    assert tuple(expand_variability_string("1-2", type_="number")) == (
        1.0,
        1.25,
        1.5,
        1.75,
        2.0,
    )
    assert tuple(expand_variability_string("1-2,5", type_="number")) == (
        1.0,
        1.25,
        1.5,
        1.75,
        2.0,
        5,
    )
