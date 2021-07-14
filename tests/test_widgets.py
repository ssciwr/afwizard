import pytest

from adaptivefiltering.widgets import WidgetForm
import jsonschema
import pyrsistent


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
