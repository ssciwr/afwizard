from adaptivefiltering.dataset import DataSet
from adaptivefiltering.filter import Filter, PipelineMixin
from adaptivefiltering.paths import load_schema
from adaptivefiltering.widgets import WidgetForm

import json
import pdal
import pyrsistent


def execute_pdal_pipeline(dataset=None, config=None):
    """Execute a PDAL pipeline

    :param dataset:
        The :class:`~adaptivefiltering.DataSet` instance that this pipeline
        operates on. If :code:`None`, the pipeline will operate without inputs.
    :type dataset: :class:`~adaptivefiltering.DataSet`
    :param config:
        The configuration of the PDAL pipeline, according to the PDAL documentation.
    :type config: dict
    :return:
        A numpy array data structure containing the PDAL output.
    :rtype: numpy.array
    """
    # Make sure that a correct combination of arguments is given
    if config is None:
        raise ValueError("PDAL Pipeline configurations is required")

    # Undo stringification of the JSON to manipulate the pipeline
    if isinstance(config, str):
        config = json.loads(config)

    # Make sure that the JSON is a list of stages, even if just the
    # dictionary for a single stage was given
    if isinstance(config, dict):
        config = [config]

    # Construct the input array argument for the pipeline
    arrays = []
    if dataset is not None:
        arrays.append(dataset.data)

    # Define and execute the pipeline
    pipeline = pdal.Pipeline(json.dumps(config), arrays=arrays)
    _ = pipeline.execute()

    # We are currently only handling situations with one output array
    assert len(pipeline.arrays) == 1

    # Return the output array
    return pipeline.arrays[0]


class PDALFilter(Filter, identifier="pdal"):
    """A filter implementation based on PDAL"""

    def execute(self, dataset):
        return DataSet(
            data=execute_pdal_pipeline(dataset=dataset, config=self._serialize())
        )

    @classmethod
    def schema(cls):
        return load_schema("pdal.json")

    def as_pipeline(self):
        return PDALPipeline(filters=[self])


class PDALPipeline(
    PipelineMixin, PDALFilter, identifier="pdal_pipeline", backend=False
):
    def execute(self, dataset):
        pipeline_json = [f["filter_data"] for f in self._serialize()["filters"]]
        return execute_pdal_pipeline(dataset=dataset, config=pipeline_json)

    def widget_form(self):
        # Provide a widget that is restricted to the PDAL backend
        schema = pyrsistent.thaw(self.schema())
        schema["properties"]["filters"] = {
            "type": "array",
            "items": Filter._filter_impls["pdal"].schema(),
        }
        return WidgetForm(pyrsistent.freeze(schema))
