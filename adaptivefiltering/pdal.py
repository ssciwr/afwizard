from adaptivefiltering.dataset import DataSet
from adaptivefiltering.filter import Filter
from adaptivefiltering.paths import locate_schema
from adaptivefiltering.widgets import WidgetForm

import json
import pdal
import pyrsistent


class PDALFilter(Filter, identifier="pdal"):
    """A filter implementation based on PDAL"""

    def __init__(self, *args, **kwargs):
        self._schema = None
        super(PDALFilter, self).__init__(*args, **kwargs)

    def execute(self, dataset, inplace=False):
        raise NotImplementedError
        pipeline = pdal.Pipeline(json.dumps([self._serialize()]))
        pipeline.execute()
        return DataSet()

    def widget_form(self):
        return PDALWidgetForm(self.schema())

    @classmethod
    def schema(cls):
        # If the schema has not been loaded, we do it now
        if getattr(cls, "_schema", None) is None:
            with open(locate_schema("pdal.json"), "r") as f:
                cls._schema = pyrsistent.freeze(json.load(f))

        return cls._schema


class PDALWidgetForm(WidgetForm):
    pass
