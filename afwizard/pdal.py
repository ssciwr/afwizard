from afwizard.dataset import DataSet
from afwizard.filter import Filter, PipelineMixin
from afwizard.paths import (
    get_temporary_filename,
    load_schema,
    locate_file,
    check_file_extension,
    within_temporary_workspace,
)
from afwizard.utils import (
    AFwizardError,
    check_spatial_reference,
)

import json
import logging
import os
import pdal
import pyrsistent

logger = logging.getLogger("afwizard")


def execute_pdal_pipeline(dataset=None, config=None):
    """Execute a PDAL pipeline

    :param dataset:
        The :class:`~afwizard.DataSet` instance that this pipeline
        operates on. If :code:`None`, the pipeline will operate without inputs.
    :type dataset: :class:`~afwizard.DataSet`
    :param config:
        The configuration of the PDAL pipeline, according to the PDAL documentation.
    :type config: dict
    :return:
        The full pdal pipeline object
    :rtype: pipeline
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

    # Check for arrays of 0 points - they throw hard to read errors in PDAL
    for array in arrays:
        if array.shape[0] == 0:
            raise AFwizardError(
                "PDAL cannot handle point clouds with 0 points, this can in some cases be caused by an out of bound segmentation or a wrong crs of the dataset."
            )

    # Define and execute the pipeline
    config_str = json.dumps(config)
    logger.info(f"Executing PDAL pipeline with configuration '{config_str}'")
    pipeline = pdal.Pipeline(config_str, arrays=arrays)

    # Execute the filter and suppress spurious file output
    _ = pipeline.execute()

    # We are currently only handling situations with one output array
    assert len(pipeline.arrays) == 1

    # Return the output pipeline
    return pipeline


class PDALFilter(Filter, identifier="pdal"):
    """A filter implementation based on PDAL"""

    def execute(self, dataset, **variability_data):
        # Apply variabilility without changing self
        config = self._modify_filter_config(variability_data)

        dataset = PDALInMemoryDataSet.convert(dataset)
        config = pyrsistent.thaw(config)
        config.pop("_backend", None)

        # Do the actual work in a temporary directory
        with within_temporary_workspace():
            pipeline = execute_pdal_pipeline(dataset=dataset, config=config)

        return PDALInMemoryDataSet(
            pipeline=pipeline,
            spatial_reference=dataset.spatial_reference,
        )

    @classmethod
    def schema(cls):
        return load_schema("pdal.json")

    @classmethod
    def form_schema(cls):
        schema = cls.schema()

        return {
            "anyOf": [
                s for s in schema["anyOf"] if s["title"] != "No-Op All Ground Filter"
            ]
        }

    def as_pipeline(self):
        return PDALPipeline(filters=[self])


class PDALPipeline(
    PipelineMixin, PDALFilter, identifier="pdal_pipeline", backend=False
):
    def execute(self, dataset, **variability_data):
        # Apply variabilility without changing self
        config = self._modify_filter_config(variability_data)

        dataset = PDALInMemoryDataSet.convert(dataset)
        pipeline_json = pyrsistent.thaw(config["filters"])
        for f in pipeline_json:
            f.pop("_backend", None)

        return PDALInMemoryDataSet(
            pipeline=execute_pdal_pipeline(dataset=dataset, config=pipeline_json),
        )


class PDALInMemoryDataSet(DataSet):
    def __init__(self, pipeline=None, spatial_reference=None):
        """An in-memory implementation of a Lidar data set that can used with PDAL

        :param pipeline:
            The numpy representation of the data set. This argument is used by e.g. filters that
            already have the dataset in memory.
        :type data: pdal.pipeline
        """
        # Store the given pipeline
        self.pipeline = pipeline
        super(PDALInMemoryDataSet, self).__init__(
            spatial_reference=spatial_reference,
        )

    @property
    def data(self):
        return self.pipeline.arrays[0]

    @classmethod
    def convert(cls, dataset):
        """Covert a dataset to a PDALInMemoryDataSet instance.

        This might involve file system based operations.

        Warning: if no srs was specified and no comp_spatialreference entry is found in the metadata this function will exit with a Warning.

        :param dataset:
            The data set instance to convert.
        """
        # Conversion should be itempotent
        if isinstance(dataset, PDALInMemoryDataSet):
            return dataset

        # save spatial reference of dataset before it is lost
        spatial_reference = dataset.spatial_reference
        # If dataset is of unknown type, we should first dump it to disk

        dataset = dataset.save(get_temporary_filename("las"))

        # Load the file from the given filename
        assert dataset.filename is not None

        filename = locate_file(dataset.filename)

        # Execute the reader pipeline
        config = {"type": "readers.las", "filename": filename}
        if spatial_reference is not None:
            config["override_srs"] = spatial_reference
            config["nosrs"] = True

        pipeline = execute_pdal_pipeline(config=[config])

        if spatial_reference is None:
            spatial_reference = pipeline.metadata["metadata"]["readers.las"][
                "comp_spatialreference"
            ]

        spatial_reference = check_spatial_reference(spatial_reference)
        return PDALInMemoryDataSet(
            pipeline=pipeline, spatial_reference=spatial_reference
        )

    def save(self, filename, overwrite=False):
        # Check if we would overwrite an input file
        filename = check_file_extension(filename, [".las", ".laz"], ".las")

        # Form the correct configuration string for compression based on file ending.

        if os.path.splitext(filename)[1] == ".las":
            compress = "none"
        elif os.path.splitext(filename)[1] == ".laz":
            compress = "laszip"

        if not overwrite and os.path.exists(filename):
            raise AFwizardError(
                f"Would overwrite file '{filename}'. Set overwrite=True to proceed"
            )

        # Exectute writer pipeline
        execute_pdal_pipeline(
            dataset=self,
            config={
                "filename": filename,
                "type": "writers.las",
                "compression": compress,
                "a_srs": self.spatial_reference,
            },
        )

        # Wrap the result in a DataSet instance
        return DataSet(
            filename=filename,
            spatial_reference=self.spatial_reference,
        )
