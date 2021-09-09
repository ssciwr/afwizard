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
import richdem as rd


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

    # Check whether we should return the full pipeline including e.g. metadata
    # Return the output pipeline
    return pipeline
    # old
    # return pipeline.arrays[0]


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
    def __init__(self, pipeline=None, provenance=[]):
        """An in-memory implementation of a Lidar data set that can used with PDAL

        :param pipeline:
            The numpy representation of the data set. This argument is used by e.g. filters that
            already have the dataset in memory.
        :type data: pdal.pipeline
        """
        # Store the given data and provenance array
        self.pipeline = pipeline

        # setup the spatial_ref history_list
        self.spatial_history = []

        super(PDALInMemoryDataSet, self).__init__(provenance=provenance)

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

        # If dataset is of unknown type, we should first dump it to disk
        dataset = dataset.save(get_temporary_filename("las"))

        # Load the file from the given filename
        assert dataset.filename is not None

        filename = locate_file(dataset.filename)

        pipeline = execute_pdal_pipeline(
            config=[
                {"type": "readers.las", "filename": filename},
                {"type": "filters.reprojection", "out_srs": "EPSG:4326"},
            ]
        )

        return PDALInMemoryDataSet(
            pipeline=pipeline,
            provenance=dataset._provenance
            + [f"Loaded {pipeline.arrays[0].shape[0]} points from {filename}"],
        )

    def save_mesh(self, filename, resolution=2.0, classification=asprs["ground"]):
        # if .tif is already in the filename it will be removed to avoid double file extension

        ang_resolution = get_angular_resolution(resolution)
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
                    "resolution": ang_resolution,
                    "default_srs": "EPSG:4326",
                    "type": "writers.gdal",
                },
            ],
        )

        # Also store the data in our internal cache
        self._mesh_data_cache[resolution, classification] = gdal.Open(
            filename + ".tif", gdal.GA_ReadOnly
        )

    def show_mesh(self, resolution=2.0, classification=asprs["ground"]):
        # check if a filename is given, if not make a temporary tif file to view data
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

    def show_slope(self, resolution=2.0, classification=asprs["ground"]):
        if self._geo_tif_data_resolution is not resolution:
            print(
                "Either no previous geotif file exists or a different resolution is requested. A new temporary geotif file with a resolution of {} will be created but not saved.".format(
                    resolution
                )
            )

        # Write a temporary file
        with tempfile.NamedTemporaryFile() as tmp_file:
            self.save_mesh(str(tmp_file.name), resolution=resolution)
            shasta_dem = rd.LoadGDAL(tmp_file.name + ".tif")

        slope = rd.TerrainAttribute(shasta_dem, attrib="slope_riserun")

        return vis_slope(slope)

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

    def show_hillshade(self, resolution=2.0, classification=asprs["ground"]):
        # check if a filename is given, if not make a temporary tif file to view data
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
        return DataSet(filename=filename)

    def restrict(self, segmentation=None):
        """
        If a segmentation is given,
        the pdal crop filter will be applied to the dataset and return the smaller dataset.

        If no segmentation is provided the user will be prompeted to draw one on a map of the dataset.


        :param segmentation:
        A Segmentation object, default: None
        :type segmentation: Segmentation

        :return:
        DataSet

        """

        if isinstance(segmentation, Segment):
            segmentation = Segmentation([segmentation])

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

    def convert_georef(self, spatial_ref_out="EPSG:4326", spatial_ref_in=None):
        """Convert the dataset from one spatial reference into another.
        This function also keeps track of all conversions that have happend.
        :parma spatial_ref_out: The desired output format. The default is the same one as in the interactive map.
        :type spatial_ref_out: string

        :param spatial_ref_in: The input format from wich the conversation is starting. The faufalt is the last transformation output.

        """
        # skip conversion if spatial out is equal to last transformation

        # if no spatial reference input is given, iterate through the metadata and search for the spatial reference input.

        if spatial_ref_in is None:

            # spacial_ref_in = json.loads(self.pipeline.metadata)["metadata"]['readers.las']["comp_spatialreference"]
            for keys, dictionary in json.loads(self.pipeline.metadata)[
                "metadata"
            ].items():
                for sub_keys, sub_dictionary in dictionary.items():
                    if sub_keys == "comp_spatialreference":
                        spatial_ref_in = sub_dictionary

        newdata = execute_pdal_pipeline(
            dataset=self,
            config={
                "type": "filters.reprojection",
                "in_srs": spatial_ref_in,
                "out_srs": spatial_ref_out,
            },
        )

        return PDALInMemoryDataSet(
            pipeline=newdata,
            provenance=self._provenance
            + [
                "converted the dataset to the {} spatial reference.".format(
                    spatial_ref_out
                )
            ],
        )
