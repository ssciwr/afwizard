from adaptivefiltering.asprs import asprs
from adaptivefiltering.paths import (
    locate_file,
    get_temporary_filename,
    load_schema,
    check_file_extension,
)
from adaptivefiltering.utils import AdaptiveFilteringError
from adaptivefiltering.visualization import visualization_dispatcher

from osgeo import gdal

import fnmatch
import ipyfilechooser
import ipywidgets
import json
import jsonschema
import os
import pytools
import shutil


class DataSet:
    def __init__(self, filename=None, spatial_reference=None):
        """The main class that represents a Lidar data set.

        The DataSet class performs lazy loading - instantiating an object of this type
        does not trigger memory intense operations until you do something with the dataset
        that requires such operation.

        :param filename:
            Filename to load the dataset from. The dataset is expected to be in LAS/LAZ 1.2-1.4 format.
            If an absolute filename is given, the dataset is loaded from that location. Relative paths
            are interpreted (in this order) with respect to the directory set with :func:`~adaptivefiltering.set_data_directory`,
            the current working directory, XDG data directories (Unix only) and the Python package
            installation directory.
        :type filename: str
        :param spatial_reference:
            A spatial reference as WKT or EPSG code. This will override the reference system found in the metadata
            and is required if no reference system is present in the metadata of the LAS/LAZ file.
            If this parameter is not provided, this information is extracted from the metadata.
        :type spatial_reference: str
        """
        # Initialize a cache data structure for rasterization operations on this data set
        self._mesh_data_cache = {}

        # Store the given parameters
        self.filename = filename
        self.spatial_reference = spatial_reference

        # Make the path absolute
        if self.filename is not None:
            self.filename = locate_file(self.filename)

    @pytools.memoize_method
    def rasterize(self, resolution=0.5, classification=None):
        """Create a digital terrain model from the dataset

        It is important to note that for archaeologic applications, the mesh is not
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
            classification = asprs(slice(None))

        if resolution <= 0:
            raise Warning("Negative Resolutions are not possible for rasterization.")

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
            Which visualization to use. Current implemented values are :code:`hillshade` for a
            greyscale 2D map and :code:`slopemap` for a 2D map color-coded by the slope
        :type visualization_type: str
        :param classification:
            Which classification values to include into the visualization. By default,
            all classes are considered. The best interface to provide this information is
            using :code:`adaptivefiltering.asprs`.
        :type classification: tuple
        :param resolution:
            The spatial resolution in meters.
        :type resolution: float
        :param azimuth:
            The angle in the xy plane where the sun is from [0, 360] (:code:`hillshade` only)
        :type azimuth: float
        :param angle_altitude:
            The angle altitude of the sun from [0, 90] (:code:`hillshade` only)
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
        """Visualize the dataset with interactive visualization controls in Jupyter"""
        from adaptivefiltering.apps import show_interactive

        return show_interactive(self)

    def save(self, filename, overwrite=False):
        """Store the dataset as a new LAS/LAZ file

        This method writes the Lidar dataset represented by this data structure
        to an LAS/LAZ file. This includes the classification values which may have
        been overriden by a filter pipeline.

        :param filename:
            Where to store the new LAS/LAZ file. You can either specify an absolute path
            or a relative path. Relative paths are interpreted w.r.t. the current
            working directory.
        :type filename: str

        :param overwrite:
            If this parameter is false and the specified filename does already exist,
            an error is thrown. This is done in order to prevent accidental corruption
            of valueable data files.
        :type overwrite: bool
        :return:
            A dataset object wrapping the written file
        :rtype: adaptivefiltering.DataSet
        """
        # check for valid file name

        filename = check_file_extension(
            filename, [".las", ".laz"], os.path.splitext(self.filename)[1]
        )
        # If the filenames match, this is a no-op operation
        if filename == self.filename:
            return self

        # Otherwise, we can simply copy the file to the new location
        # after checking that we are not accidentally overriding something
        if not overwrite and os.path.exists(filename):
            raise AdaptiveFilteringError(
                f"Would overwrite file '{filename}'. Set overwrite=True to proceed"
            )

        # check if file extension changed.

        if os.path.splitext(filename)[1] == os.path.splitext(self.filename)[1]:

            # Do the copy operation
            shutil.copy(self.filename, filename)

            # And return a DataSet instance
            return DataSet(
                filename=filename,
                spatial_reference=self.spatial_reference,
            )

        # if the file extension changed the pdal save function will be called.

        else:
            from adaptivefiltering.pdal import PDALInMemoryDataSet

            ds_pdal = PDALInMemoryDataSet.convert(self)
            return ds_pdal.save(filename, overwrite)

    def restrict(self, segmentation=None):
        """Restrict the data set to a spatial subset

        This is of vital importance when working with large Lidar datasets
        in adaptivefiltering. The interactive exploration process for filtering
        pipelines requires a reasonably sized subset to allow fast previews.

        :param segmentation:
            A segmentation object that provides the geometric information
            for the cropping. If omitted, an interactive selection tool is
            shown in Jupyter.
        :type: adaptivefiltering.segmentation.Segmentation
        """

        from adaptivefiltering.apps import apply_restriction

        return apply_restriction(self, segmentation)

    @classmethod
    def convert(cls, dataset):
        """Convert this dataset to an instance of DataSet

        This is used internally to convert datasets between different
        representations.

        :return:
            A dataset with transformed datapoints.
        :rtype: adaptivefiltering.DataSet
        """
        return dataset.save(get_temporary_filename(extension="las"))


class DigitalSurfaceModel:
    def __init__(self, dataset=None, **rasterization_options):
        """Representation of a rasterized DEM/DTM/DSM/DFM

        Constructs a raster model from a dataset. This is typically used
        implicitly or through :func:`~adaptivefiltering.DataSet.rasterize`.
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
                    for c in rasterization_options.get(
                        "classification", asprs(slice(None))
                    )
                ),
            }
        ]

        # If we are only using ground, we use a triangulation approach
        if tuple(rasterization_options.get("classification", asprs(slice(None)))) == (
            2,
        ):
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
        vis = visualization_dispatcher(self, **kwargs)
        vis.layout = ipywidgets.Layout(width="70%")
        box_layout = ipywidgets.Layout(
            width="100%", flex_flow="column", align_items="center", display="flex"
        )

        # Controls for saving this image
        patterns = {"PNG": "*.png", "GeoTiff": "*.tiff", "LAS": "*.las", "LAZ": "*.laz"}
        selector = ipywidgets.Dropdown(
            options=["PNG", "GeoTiff", "LAS", "LAZ"],
            value="PNG",
            description="Type:",
            layout=ipywidgets.Layout(width="50%"),
        )
        filename = ipyfilechooser.FileChooser(
            filter_pattern=patterns[selector.value],
            layout=ipywidgets.Layout(width="100%"),
        )
        button = ipywidgets.Button(
            description="Save this image!", layout=ipywidgets.Layout(width="50%")
        )

        # Put these together into one control widget
        controls = ipywidgets.VBox(
            children=[
                ipywidgets.HBox(
                    children=[selector, button], layout=ipywidgets.Layout(width="100%")
                ),
                filename,
            ],
            layout=ipywidgets.Layout(width="100%"),
        )

        def _update_pattern(_):
            # Set the new pattern
            filename.filter_pattern = patterns[selector.value]

            # If the current value does not match the pattern remove it
            if filename.value and not fnmatch.fnmatch(
                filename.value, filename.filter_pattern
            ):
                filename.reset()

        selector.observe(_update_pattern, names="value")

        def _save_to_file(_):
            if filename.value:
                # We already have the GeoTiff file in a temporary directory - simple copy
                if selector.value == "GeoTiff":
                    shutil.copy(self.filename, filename.value)

                # For PNGs we need to write the binary buffer to file
                if selector.value == "PNG":
                    with open(filename.value, "wb") as f:
                        f.write(vis.value)

                # LAS/LAZ export is simple, just access the underlying dataset
                if selector.value == "LAS":
                    self.dataset.save(filename.value, compress=False, overwrite=False)

                if selector.value == "LAZ":
                    self.dataset.save(filename.value, compress=True, overwrite=True)

        button.on_click(_save_to_file)

        return ipywidgets.HBox(
            children=[
                vis,
                controls,
            ],
            layout=box_layout,
        )


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
    print(dataset.filename)
    return PDALInMemoryDataSet(
        pipeline=pipeline,
        spatial_reference=dataset.spatial_reference,
        filename=dataset.filename,
    )


def reproject_dataset(dataset, out_srs, in_srs=None):
    """Standalone function to reproject a given dataset with the option of forcing an input reference system

    :param out_srs:
        The desired output format in WKT.
    :type out_srs: str
    :param in_srs:
        The input format in WKT from which to convert. The default is the dataset's current reference system.
    :type in_srs: str
    :return:
        A reprojected dataset
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
        spatial_reference=spatial_reference,
        filename=dataset.filename,
    )
