from adaptivefiltering.widgets import *

import jsonschema
import pyrsistent
import pytest


_example_schema = [
    {
        "type": "object",
        "properties": {
            "price": {"type": "number"},
            "name": {"type": "string", "const": "This is a constant"},
        },
    },
    {
        "type": "object",
        "properties": {"things": {"type": "array", "items": {"enum": ["A", "B"]}}},
    },
    {
        "type": "object",
        "properties": {
            "nested": {"type": "object", "properties": {"foo": {"type": "boolean"}}},
            "name": {"type": "string"},
        },
    },
]


@pytest.mark.parametrize("schema", _example_schema)
def test_widget_form(schema):
    widget = WidgetForm(schema)
    widget.show()
    jsonschema.validate(instance=pyrsistent.thaw(widget.data), schema=schema)

    # Get data, set it, get it again and compare the resulting document
    data = widget.data
    widget.data = data
    data2 = widget.data
    assert data == data2


def test_pattern_rule():
    schema = {"type": "string", "pattern": "[^_-]*"}
    widget = WidgetForm(schema)
    widget.data = "blawithoutdashor underscore"

    with pytest.raises(WidgetFormError):
        widget.data = "ba_ad"
