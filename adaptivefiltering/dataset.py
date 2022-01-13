from adaptivefiltering.asprs import asprs
from adaptivefiltering.paths import locate_file, get_temporary_filename, load_schema
from adaptivefiltering.utils import AdaptiveFilteringError, check_spatial_reference
from adaptivefiltering.visualization import gdal_visualization

from osgeo import gdal

import ipywidgets
import json
import jsonschema
import os
import pytools
import shutil
import sys
import tempfile


class DataSet:
    def __init__(self, filename=None, provenance=[], spatial_reference=None):
        """The main class that represents a Lidar data set.
        :param filename:
            Filename to load the dataset from. The dataset is expected to be in LAS/LAZ 1.2-1.4 format.
            If an absolute filename is given, the dataset is loaded from that location. Relative paths
            are interpreted (in this order) with respect to the directory set with :func:`~adaptivefiltering.set_data_directory`,
            the current working directory, XDG data directories (Unix only) and the Python package
            installation directory.
            Will give a warning if too many data points are present.
        :type filename: str
        :param spatial_reference:
            A spatial reference in WKT or EPSG code. This will override the reference system found in the metadata
            and is required if no reference system is present in the metadata of the LAS/LAZ file.
            If this parameter is not provided, this information is extracted from the metadata.
        :type spatial_reference: str
        """
        # Initialize a cache data structure for rasterization operations on this data set
        self._mesh_data_cache = {}

        # Store the given parameters
        self._provenance = provenance
        self.filename = filename
        self.spatial_reference = spatial_reference

        # Make the path absolute
        if self.filename is not None:
            self.filename = locate_file(self.filename)

    @pytools.memoize_method
    def rasterize(self, resolution=0.5, classification=None):
        """Create a digital terrain model from the dataset

        It is important to note that for archaelogic applications, the mesh is not
        a traditional DEM/DTM (Digitial Elevation/Terrain Model), but rather a DFM
        (Digital Feature Model) which consists of ground and all potentially relevant
        structures like buildings etc. but always excludes vegetation.

        :param resolution:
            The mesh resolution in meters. Adapt this depending on the scale
            of the features you are looking for and the point density of your
            Lidar data.
        :type resolution: float
        :param classification:
            The classification values to include into the written mesh file.
        :type classification: tuple
        """
        # If no classification value was given, we use all classes
        if classification is None:
            classification = asprs[:]

        return DigitalSurfaceModel(
            dataset=self, resolution=resolution, classification=classification
        )

    def show(self, visualization_type="hillshade", **kwargs):
        """Visualize the dataset in JupyterLab
        Several visualization options can be chosen via the *visualization_type* parameter.
        Some of the arguments given below are only available for specific visualization
        types. To explore the visualization capabilities, you can also use the interactive
        user interface with :func:`~adaptivefiltering.DataSet.show_interactive`.
        :param visualization_type:
            Which visualization to use. Current implemented values are:
            * `hillshade` for a greyscale 2D map
            * `slopemap` for a 2D map color-coded by the slope
            * `scatter` for a 3D scatter plot of the point cloud
            * `mesh` for a 2.5D surface plot
        :type visualization_type: str
        :param classification:
            Which classification values to include into the visualization. By default,
            all classes are considered. The best interface to provide this information is
            using :ref:`~adaptivefilter.asprs`.
        :type classification: tuple
        :param resolution:
            The spatial resolution in meters (needed for all types except `scatter`).
        :type resolution: float
        :param azimuth:
            The angle in the xy plane where the sun is from [0, 360] (`hillshade` only)
        :type azimuth: float
        :param angle_altitude:
            The angle altitude of the sun from [0, 90] (`hillshade` only)
        """

        # This is a bit unfortunate, but we need to separate rasterization options
        # from visualization options. I have not had a better idea how to do this.
        raster_schema = load_schema("rasterize.json")
        rasterize_options = {}
        for key in raster_schema["properties"].keys():
            if key in kwargs:
                rasterize_options[key] = kwargs.pop(key)

        # Defer visualization to the rastered dataset
        return self.rasterize(**rasterize_options).show(
            visualization_type=visualization_type, **kwargs
        )

    def show_interactive(self):
        """Visualize the dataset with interactive visualization controls"""
        from adaptivefiltering.apps import show_interactive

        return show_interactive(self)

    def save(self, filename, compress=False, overwrite=False):
        """Store the dataset as a new LAS/LAZ file
        This writes this instance of the data set to an LAS/LAZ file which will
        permanently store the ground point classification. The resulting file will
        also contain the point data from the original data set.
        :param filename:
            Where to store the new LAS/LAZ file. You can either specify an absolute path
            or a relative path. Relative paths are interpreted w.r.t. the current
            working directory.
        :type filename: str
        :param compress:
            If true, an LAZ file will be written instead of an LAS file.
        :type compress: bool
        :param overwrite:
            If this parameter is false and the specified filename does already exist,
            an error is thrown. This is done in order to prevent accidental corruption
            of valueable data files.
        :type overwrite: bool
        :return:
            A dataset object wrapping the written file
        :rtype: adaptivefiltering.DataSet
        """
        # If the filenames match, this is a no-op operation
        if filename == self.filename:
            return self

        # Otherwise, we can simply copy the file to the new location
        # after checking that we are not accidentally overriding something
        if not overwrite and os.path.exists(filename):
            raise AdaptiveFilteringError(
                f"Would overwrite file '{filename}'. Set overwrite=True to proceed"
            )

        # Do the copy operation
        shutil.copy(self.filename, filename)

        # And return a DataSet instance
        return DataSet(
            filename=filename,
            provenance=self._provenance,
            spatial_reference=self.spatial_reference,
        )

    def restrict(self, segmentation=None):
        """Restrict the data set to a spatial subset
        :param segmentation:
        :type: adaptivefiltering.segmentation.Segmentation
        """
        from adaptivefiltering.pdal import PDALInMemoryDataSet

        dataset = PDALInMemoryDataSet.convert(self)

        return dataset.restrict(segmentation)

    def provenance(self, stream=sys.stdout):
        """Report the provence of this data set
        For the given data set instance, report the input data and filter
        sequence (incl. filter settings) that procuced this data set. This
        can be used to make good filtering results achieved while using the
        package reproducible.
        :param stream:
            The stream to write the results to. Defaults to stdout, but
            could also e.g. be a file stream.
        """

        stream.write("Provenance report generated by adaptivefiltering:\n\n")
        for i, entry in self._provenance:
            stream.write(f"Item #{i}:\n")
            stream.write(f"{entry}\n\n")

    @classmethod
    def convert(cls, dataset):
        """Convert this dataset to an instance of DataSet"""
        return dataset.save(get_temporary_filename(extension="las"))


class DigitalSurfaceModel:
    def __init__(self, dataset=None, **rasterization_options):
        """Representation of a rasterized DEM/DTM/DSM/DFM

        Constructs a raster model from a dataset. This is typically used
        implicitly or through :ref:`~adaptivefilter.DataSet.rasterize`.
        """

        from adaptivefiltering.pdal import PDALInMemoryDataSet, execute_pdal_pipeline

        # Store a reference to the generating dataset
        self.dataset = PDALInMemoryDataSet.convert(dataset)

        # Validate the provided options
        schema = load_schema("rasterize.json")
        jsonschema.validate(
            rasterization_options, schema=schema, types=dict(array=(list, tuple))
        )

        # Get a temporary filename to write the geotiff to
        self.filename = get_temporary_filename()

        # Create the PDAL filter configuration
        config = [
            {
                "type": "filters.range",
                "limits": ",".join(
                    f"Classification[{c}:{c}]"
                    for c in rasterization_options.get("classification", asprs[:])
                ),
            }
        ]

        # If we are only using ground, we use a triangulation approach
        if tuple(rasterization_options.get("classification", asprs[:])) == (2,):
            config.extend(
                [
                    {
                        "type": "filters.delaunay",
                    },
                    {
                        "type": "filters.faceraster",
                        "resolution": rasterization_options.get("resolution", 0.5),
                    },
                    {
                        "type": "writers.raster",
                        "filename": self.filename,
                    },
                ]
            )
        else:
            # Otherwise, a non-triangulated approach gives the better result
            config.append(
                {
                    "filename": self.filename,
                    "gdaldriver": "GTiff",
                    "output_type": "all",
                    "type": "writers.gdal",
                    "resolution": rasterization_options.get("resolution", 0.5),
                }
            )

        # Create the model by running the pipeline
        execute_pdal_pipeline(
            dataset=self.dataset,
            config=config,
        )

        self.raster = gdal.Open(self.filename, gdal.GA_ReadOnly)

    def show(self, visualization_type="hillshade", **kwargs):
        # Validate the visualization input
        kwargs["visualization_type"] = visualization_type
        schema = load_schema("visualization.json")
        jsonschema.validate(kwargs, schema=schema)

        # Call the correct visualization function
        vis = gdal_visualization(self, **kwargs)
        vis.layout = ipywidgets.Layout(width="70%")
        box_layout = ipywidgets.Layout(
            width="100%", flex_flow="column", align_items="center", display="flex"
        )
        return ipywidgets.HBox(children=[vis], layout=box_layout)


def remove_classification(dataset):
    """Remove the classification values from a Lidar dataset
    Instead, all points will be classified as 1 (unclassified). This is useful
    to drop an automatic preclassification in order to create an archaelogically
    relevant classification from scratch.
    :param dataset:
        The dataset to remove the classification from
    :type dataset: adaptivefiltering.Dataset
    :return:
        A transformed dataset with unclassified points
    :rtype: adaptivefiltering.DataSet
    """
    from adaptivefiltering.pdal import PDALInMemoryDataSet, execute_pdal_pipeline

    dataset = PDALInMemoryDataSet.convert(dataset)
    pipeline = execute_pdal_pipeline(
        dataset=dataset,
        config={"type": "filters.assign", "value": ["Classification = 1"]},
    )

    return PDALInMemoryDataSet(
        pipeline=pipeline,
        provenance=dataset._provenance + ["Removed all point classifications"],
        spatial_reference=dataset.spatial_reference,
    )


def reproject_dataset(dataset, out_srs, in_srs=None):
    """
    Standalone function to reproject a given dataset with the option of forcing an input reference system
    :param out_srs: The desired output format in WKT.
    :type out_srs: str
    :param in_srs: The input format in WKT from which to convert. The default is the dataset's current reference system.
    :type in_srs: str
    :return: A reprojected dataset
    :rtype: adaptivefiltering.DataSet
    """
    from adaptivefiltering.pdal import execute_pdal_pipeline
    from adaptivefiltering.pdal import PDALInMemoryDataSet

    dataset = PDALInMemoryDataSet.convert(dataset)
    if in_srs is None:
        in_srs = dataset.spatial_reference

    config = {
        "type": "filters.reprojection",
        "in_srs": in_srs,
        "out_srs": out_srs,
    }
    pipeline = execute_pdal_pipeline(dataset=dataset, config=config)
    spatial_reference = json.loads(pipeline.metadata)["metadata"][
        "filters.reprojection"
    ]["comp_spatialreference"]
    return PDALInMemoryDataSet(
        pipeline=pipeline,
        provenance=dataset._provenance
        + [f"Converted the dataset to spatial reference system '{out_srs}'"],
        spatial_reference=spatial_reference,
    )
