from typing import Counter
from pdal import pipeline
from adaptivefiltering.asprs import asprs
from adaptivefiltering.dataset import DataSet
from adaptivefiltering.filter import Filter, PipelineMixin
from adaptivefiltering.paths import get_temporary_filename, load_schema, locate_file
from adaptivefiltering.segmentation import Segment, Segmentation
from adaptivefiltering.visualization import (
    vis_hillshade,
    vis_mesh,
    vis_pointcloud,
    vis_slope,
)
from adaptivefiltering.utils import AdaptiveFilteringError, get_angular_resolution
from adaptivefiltering.widgets import WidgetForm

import functools
import geodaisy.converters as convert
from osgeo import gdal
import json
import numpy as np
import os
import pdal
import pyrsistent
import tempfile
import richdem


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

    # Define and execute the pipeline
    pipeline = pdal.Pipeline(json.dumps(config), arrays=arrays)
    _ = pipeline.execute()

    # We are currently only handling situations with one output array
    assert len(pipeline.arrays) == 1

    # Return the output pipeline
    return pipeline


class PDALFilter(Filter, identifier="pdal"):
    """A filter implementation based on PDAL"""

    def execute(self, dataset):
        dataset = PDALInMemoryDataSet.convert(dataset)
        config = pyrsistent.thaw(self.config)
        config.pop("_backend", None)
        return PDALInMemoryDataSet(
            pipeline=execute_pdal_pipeline(dataset=dataset, config=config),
            provenance=dataset._provenance
            + [f"Applying PDAL filter with the following configuration:\n{config}"],
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
        dataset = PDALInMemoryDataSet.convert(dataset)
        pipeline_json = pyrsistent.thaw(self.config["filters"])
        for f in pipeline_json:
            f.pop("_backend", None)

        return PDALInMemoryDataSet(
            pipeline=execute_pdal_pipeline(dataset=dataset, config=pipeline_json),
            provenance=dataset._provenance
            + [
                f"Applying PDAL pipeline with the following configuration:\n{pipeline_json}"
            ],
        )


class PDALInMemoryDataSet(DataSet):
    def __init__(
        self, pipeline=None, provenance=[], georeferenced=True, spatial_reference=None
    ):
        """An in-memory implementation of a Lidar data set that can used with PDAL

        :param pipeline:
            The numpy representation of the data set. This argument is used by e.g. filters that
            already have the dataset in memory.
        :type data: pdal.pipeline
        """
        # Store the given data and provenance array
        self.pipeline = pipeline

        super(PDALInMemoryDataSet, self).__init__(
            provenance=provenance,
            georeferenced=georeferenced,
            spatial_reference=spatial_reference,
        )

    @property
    def data(self):
        return self.pipeline.arrays[0]

    @classmethod
    def convert(cls, dataset):
        """Covert a dataset to a PDALInMemoryDataSet instance.

        This might involve file system based operations.

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

        # Conditionally define a reprojection filter
        reproj_filter = []
        if dataset.georeferenced:
            reproj_filter.append(
                {"type": "filters.reprojection", "out_srs": "EPSG:4326"}
            )

        # Execute the reader pipeline
        config = {"type": "readers.las", "filename": filename}
        if spatial_reference is not None:
            config["override_srs"] = spatial_reference
            config["nosrs"] = True

        pipeline = execute_pdal_pipeline(
            # config=[{"type": "readers.las", "filename": filename}]   + reproj_filter
            config=[config]
        )

        if spatial_reference is None:
            spatial_reference = json.loads(pipeline.metadata)["metadata"][
                "readers.las"
            ]["comp_spatialreference"]
            # hanlde empty metadata
            if spatial_reference.strip() == "":
                raise Warning(
                    "No SRS was detected, please include one manually if non is present in the LAS file."
                )

        return PDALInMemoryDataSet(
            pipeline=pipeline,
            provenance=dataset._provenance
            + [f"Loaded {pipeline.arrays[0].shape[0]} points from {filename}"],
            georeferenced=dataset.georeferenced,
            spatial_reference=spatial_reference,
        )

    def save_mesh(self, filename, resolution=2.0, classification=asprs["ground"]):
        # if .tif is already in the filename it will be removed to avoid double file extension

        # resolution_options = {}
        # if self.georeferenced:
        #     resolution_options["resolution"] = get_angular_resolution(resolution)
        #     resolution_options["default_srs"] = "EPSG:4326"
        # else:
        #     resolution_options["resolution"] = resolution
        print(resolution)
        if os.path.splitext(filename)[1] == ".tif":
            filename = os.path.splitext(filename)[0]
        execute_pdal_pipeline(
            dataset=self,
            config=[
                {
                    "type": "filters.range",
                    "limits": ",".join(
                        f"Classification[{c}:{c}]" for c in classification
                    ),
                },
                {
                    "filename": filename + ".tif",
                    "gdaldriver": "GTiff",
                    "output_type": "all",
                    "type": "writers.gdal",
                    "resolution": resolution,
                },
            ],
        )

        # Also store the data in our internal cache
        self._mesh_data_cache[resolution, classification] = gdal.Open(
            filename + ".tif", gdal.GA_ReadOnly
        )

    def show_mesh(self, resolution=2.0, classification=asprs["ground"]):
        # make a temporary tif file to view data
        if (resolution, classification) not in self._mesh_data_cache:
            # Write a temporary file
            with tempfile.NamedTemporaryFile() as tmp_file:
                self.save_mesh(
                    str(tmp_file.name),
                    resolution=resolution,
                    classification=classification,
                )

        # Retrieve the raster data from cache
        data = self._mesh_data_cache[resolution, classification]

        # use the number of x and y points to generate a grid.
        x = np.arange(0, data.RasterXSize)
        y = np.arange(0, data.RasterYSize)

        # multiplay x and y with the given resolution for comparable plot.
        x = x * data.GetGeoTransform()[1]
        y = y * data.GetGeoTransform()[1]

        # get height information from
        band = data.GetRasterBand(1)
        z = band.ReadAsArray()

        return vis_mesh(x, y, z)

    def show_points(self, threshold=750000, classification=asprs["ground"]):
        if len(self.data["X"]) >= threshold:
            error_text = "Too many Datapoints loaded for visualisation.{} points are loaded, but only {} allowed".format(
                len(self.data["X"]), threshold
            )
            raise ValueError(error_text)

        filtered_data = self.data[
            functools.reduce(
                np.logical_or,
                (self.data["Classification"] == c for c in classification),
            )
        ]

        return vis_pointcloud(
            filtered_data["X"], filtered_data["Y"], filtered_data["Z"]
        )

    def show_slope(self, resolution=2.0, classification=asprs["ground"]):
        # make a temporary tif file to view data

        with tempfile.NamedTemporaryFile() as tmp_file:
            self.save_mesh(
                str(tmp_file.name),
                resolution=resolution,
                classification=classification,
            )
            shasta_dem = richdem.LoadGDAL(tmp_file.name + ".tif")

        slope = richdem.TerrainAttribute(shasta_dem, attrib="slope_riserun")

        return vis_slope(slope)

    def show_hillshade(self, resolution=2.0, classification=asprs["ground"]):
        # make a temporary tif file to view data
        if (resolution, classification) not in self._mesh_data_cache:
            # Write a temporary file
            with tempfile.NamedTemporaryFile() as tmp_file:
                self.save_mesh(
                    str(tmp_file.name),
                    resolution=resolution,
                    classification=classification,
                )

        # Retrieve the raster data from cache
        data = self._mesh_data_cache[resolution, classification]

        band = data.GetRasterBand(1)

        return vis_hillshade(band.ReadAsArray())

    def save(self, filename, compress=False, overwrite=False):
        # Check if we would overwrite an input file
        if not overwrite and os.path.exists(filename):
            raise AdaptiveFilteringError(
                f"Would overwrite file '{filename}'. Set overwrite=True to proceed"
            )

        # Form the correct configuration string for compression
        compress = "laszip" if compress else "none"

        # Exectute writer pipeline
        execute_pdal_pipeline(
            dataset=self,
            config={
                "filename": filename,
                "type": "writers.las",
                "compression": compress,
            },
        )

        # Wrap the result in a DataSet instance
        return DataSet(filename=filename, georeferenced=self.georeferenced)

    def restrict(self, segmentation=None):
        # If a single Segment is given, we convert it to a segmentation

        if isinstance(segmentation, Segment):
            segmentation = Segmentation([segmentation.__geo_interface__])

        def apply_restriction(seg):
            # raise an Error if two polygons are given.
            if len(seg["features"]) > 1:
                raise NotImplementedError(
                    "The function to choose multiple segments at the same time is not implemented yet."
                )
            # Construct an array of WKT Polygons for the clipping
            polygons = [convert.geojson_to_wkt(s["geometry"]) for s in seg["features"]]

            from adaptivefiltering.pdal import execute_pdal_pipeline

            # Apply the cropping filter with all polygons
            newdata = execute_pdal_pipeline(
                dataset=self, config={"type": "filters.crop", "polygon": polygons}
            )

            return PDALInMemoryDataSet(
                pipeline=newdata,
                provenance=self._provenance
                + [
                    f"Cropping data to only include polygons defined by:\n{str(polygons)}"
                ],
            )

        # Maybe create the segmentation
        if segmentation is None:
            from adaptivefiltering.apps import create_segmentation

            restricted = create_segmentation(self)
            restricted._finalization_hook = apply_restriction

            return restricted
        else:
            return apply_restriction(segmentation)
