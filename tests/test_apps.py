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
