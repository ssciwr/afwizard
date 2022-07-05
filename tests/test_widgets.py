from afwizard.widgets import *

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


def test_widget_form_with_labels_pattern():
    schema = {
        "items": {"pattern": "[a-z\\-]*", "type": "string"},
        "type": "array",
    }

    form = WidgetFormWithLabels(schema)

    # Set with some valid and some non-valid data
    form.data = ["bla", "bla2", "bla-bla", "bla_bla"]
    assert len(form.data) == 2
    assert form.data[0] == "bla"
    assert form.data[1] == "bla-bla"


@pytest.mark.parametrize("schema", _example_schema)
def test_batchdata_getset(schema):
    widget = BatchDataWidgetForm(schema)

    # Get data, set it, get it again and compare the resulting document
    data = widget.batchdata
    widget.batchdata = data
    data2 = widget.batchdata

    assert pyrsistent.freeze(data) == pyrsistent.freeze(data2)
