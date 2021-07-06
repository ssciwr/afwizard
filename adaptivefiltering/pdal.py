from adaptivefiltering.filter import Filter
from adaptivefiltering.widgets import WidgetForm

import json
import pyrsistent


class PDALFilter(Filter, identifier="pdal"):
    """A filter implementation based on PDAL"""

    def widget_form(self):
        return PDALWidgetForm(self.schema)

    @property
    def schema(self):
        return pyrsistent.freeze(
            {
                "anyOf": [
                    {
                        "title": "Crop (PDAL)",
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "const": "filters.crop"},
                            "point": {"type": "string"},
                            "distance": {"type": "number"},
                        },
                    },
                    {
                        "title": "Cloth Simulation Filter (PDAL)",
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "const": "filters.csf"}
                        },
                    },
                ]
            }
        )


class PDALWidgetForm(WidgetForm):
    pass
