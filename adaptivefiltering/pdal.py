from adaptivefiltering.filter import Filter
from adaptivefiltering.paths import locate_schema
from adaptivefiltering.widgets import WidgetForm

import json
import pyrsistent


class PDALFilter(Filter, identifier="pdal"):
    """A filter implementation based on PDAL"""

    def __init__(self, *args, **kwargs):
        self._schema = None
        super(PDALFilter, self).__init__(*args, **kwargs)

    def widget_form(self):
        return PDALWidgetForm(self.schema)

    @property
    def schema(self):
        # If the schema has not been loaded, we do it now
        if self._schema is None:
            with open(locate_schema("pdal.json"), "r") as f:
                self._schema = pyrsistent.freeze(json.load(f))

        return self._schema


class PDALWidgetForm(WidgetForm):
    pass
