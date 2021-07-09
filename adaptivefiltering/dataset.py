from adaptivefiltering.paths import locate_file
from adaptivefiltering.visualization import vis_pointcloud, vis_mesh

import json
import laspy
import pdal
import tempfile
import numpy as np
from osgeo import gdal
import os
import sys


class DataSet:
    def __init__(self, filename, warning_threshold=750000):
        """The main class that represents a Lidar data set.

        :param filename:
            Filename to load the dataset from. The dataset is expected to be in LAS/LAZ 1.2-1.4 format.
            If an absolute filename is given, the dataset is loaded from that location. Relative paths
            are interpreted (in this order) with respect to the directory set with :any:`set_data_directory`,
            the current working directory, XDG data directories (Unix only) and the Python package
            installation directory.
            Will give a warning if too many data points are present.
        :type filename: str
        """
        # initilizise self._geo_tif_data_resolution as 0
        self._geo_tif_data_resolution = 0
        # initilize warning threshold to warn the user that show() is not available
        self.warning_threshold = warning_threshold

        self.filename = locate_file(filename)
        # old laspy style
        # self.data = laspy.file.File(filename, mode="r")

        # new laspy style
        # test = laspy.read(test, l)
        self.data = laspy.read(self.filename)

        if len(self.data.x) >= self.warning_threshold:
            print(
                "This is a warning: {} points are loaded, but only {} can be displayed via the show() function".format(
                    len(self.data.x), self.warning_threshold
                )
            )

    def save_mesh(
        self,
        filename,
        resolution=2.0,
    ):
        """Store the point cloud as a digital terrain model to a GeoTIFF file

        It is important to note that for archaelogic applications, the mesh is not
        a traditional DEM/DTM (Digitial Elevation/Terrain Model), but rather a DFM
        (Digital Feature Model) which consists of ground and all potentially relevant
        structures like buildings etc. but always excludes vegetation.

        :param filename:
            The filename to store the mesh. You can either specify an absolute path
            or a relative path. Relative paths are interpreted w.r.t. the current
            working directory.
        :type filename: str
        :param resolution:
            The mesh resolution in meters. Adapt this depending on the scale
            of the features you are looking for and the point density of your
            Lidar data.
        :type resolution: float
        """
        # if .tif is already in the filename it will be removed to avoid double file extension
        if os.path.splitext(filename)[1] == ".tif":
            filename = os.path.splitext(filename)[0]
        # configure the geotif pipeline
        geotif_pipeline_json = [
            self.filename,
            {
                "filename": filename + ".tif",
                "gdaldriver": "GTiff",
                "output_type": "all",
                "resolution": resolution,
                "type": "writers.gdal",
            },
        ]
        # setup and execute the geotif pipeline
        pipeline = pdal.Pipeline(json.dumps(geotif_pipeline_json))
        geotif_pipeline = pipeline.execute()
        self._geo_tif_data = gdal.Open(filename + ".tif", gdal.GA_ReadOnly)
        self._geo_tif_data_resolution = resolution

    def show_mesh(self, resolution=2.0):
        """Visualize the point cloud as a digital terrain model in JupyterLab

        It is important to note that for archaelogic applications, the mesh is not
        a traditional DEM/DTM (Digitial Elevation/Terrain Model), but rather a DFM
        (Digital Feature Model) which consists of ground and all potentially relevant
        structures like buildings etc. but always excludes vegetation.

        :param resolution:
            The mesh resolution in meters. Adapt this depending on the scale
            of the features you are looking for and the point density of your
            Lidar data.
        :type resolution: float
        """

        # check if a filename is given, if not make a temporary tif file to view data
        if self._geo_tif_data_resolution is not resolution:
            print(
                "Either no previous geotif file exists or a different resolution is requested. A new temporary geotif file with a resolution of {} will be created but not saved.".format(
                    resolution
                )
            )

            # the temporary file is not removed automatically. Manual removal will be implemented
            with tempfile.NamedTemporaryFile(dir=os.getcwd()) as tmp_file:
                self.save_mesh(str(tmp_file.name), resolution=resolution)

        # use the number of x and y points to generate a grid.
        x = np.arange(0, self._geo_tif_data.RasterXSize)
        y = np.arange(0, self._geo_tif_data.RasterYSize)

        # multiplay x and y with the given resolution for comparable plot.
        x = x * self._geo_tif_data.GetGeoTransform()[1]
        y = y * self._geo_tif_data.GetGeoTransform()[1]

        # get height information from
        band = self._geo_tif_data.GetRasterBand(1)
        z = band.ReadAsArray()
        return vis_mesh(x, y, z)

    def show(self):
        """Visualize the point cloud in Jupyter notebook
        Will give a warning if too many data points are present.
        Non-operational if called outside of Jupyter Notebook.
        """
        if len(self.data.x) >= self.warning_threshold:
            error_text = "Too many Datapoints loaded for visualisation.{} points are loaded, but only {} allowed".format(
                len(self.data.x), self.warning_threshold
            )
            raise ValueError(error_text)

        return vis_pointcloud(self.data.x, self.data.y, self.data.z)

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
        """
        raise NotImplementedError  # pragma: no cover

    def restrict(self, segmentation):
        """Restrict the data set to a spatial subset

        :param segmentation:
        :type: adaptivefiltering.segmentation.Segmentation
        """
        raise NotImplementedError  # pragma: no cover

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
        raise NotImplementedError  # pragma: no cover
