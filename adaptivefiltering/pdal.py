from adaptivefiltering.dataset import DataSet
from adaptivefiltering.filter import Filter, PipelineMixin
from adaptivefiltering.paths import locate_schema
from adaptivefiltering.widgets import WidgetForm

import json
import pdal
import pyrsistent


def execute_pdal_pipeline(dataset, pipeline_json):
    """Execute a PDAL pipeline defined as JSON"""
    # Undo stringification of the JSON to manipulate the pipeline
    if isinstance(pipeline_json, str):
        pipeline_json = json.loads(pipeline_json)

    # Make sure that the JSON is a list of stages, even if just the
    # dictionary for a single stage was given
    if isinstance(pipeline_json, dict):
        pipeline_json = [pipeline_json]

    # Add the input filename to the pipeline
    pipeline_json = [dataset.filename] + pipeline_json

    # Define and execute the pipeline
    pipeline = pdal.Pipeline(json.dumps(pipeline_json))
    pipeline.execute()


class PDALFilter(Filter, identifier="pdal"):
    """A filter implementation based on PDAL"""

    def __init__(self, *args, **kwargs):
        self._schema = None
        super(PDALFilter, self).__init__(*args, **kwargs)

    def execute(self, dataset, inplace=False):
        return execute_pdal_pipeline(dataset, self._serialize())

    def widget_form(self):
        return PDALWidgetForm(self.schema())

    @classmethod
    def schema(cls):
        # If the schema has not been loaded, we do it now
        if getattr(cls, "_schema", None) is None:
            with open(locate_schema("pdal.json"), "r") as f:
                cls._schema = pyrsistent.freeze(json.load(f))

        return cls._schema

    def as_pipeline(self):
        return PDALPipeline(filters=[self])


class PDALPipeline(
    PipelineMixin, PDALFilter, identifier="pdal_pipeline", backend=False
):
    def execute(self, dataset, inplace=False):
        pipeline_json = [f["filter_data"] for f in self._serialize()["filters"]]
        return execute_pdal_pipeline(dataset, pipeline_json)

    def widget_form(self):
        # Provide a widget that is restricted to the PDAL backend
        schema = pyrsistent.thaw(self.schema())
        schema["properties"]["filters"] = {
            "type": "array",
            "items": Filter._filter_impls["pdal"].schema(),
        }
        return WidgetForm(pyrsistent.freeze(schema))


class PDALWidgetForm(WidgetForm):
    pass
