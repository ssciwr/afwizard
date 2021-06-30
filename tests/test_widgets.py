import pytest

from adaptivefiltering.widgets import WidgetForm
import jsonschema


_example_schema = [
    {
        "$schema": "https://json-schema.org/schema#",
        "type": "object",
        "properties": {
            "price": {"type": "number"},
            "name": {"type": "string"},
        },
    }
]


@pytest.mark.parametrize("schema", _example_schema)
def test_widget_form(schema):
    widget = WidgetForm(schema)
    widget.show()
    jsonschema.validate(instance=widget.data(), schema=schema)
