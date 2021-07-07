from adaptivefiltering.visualization import vis_pointcloud
from adaptivefiltering.visualization import vis_mesh
from adaptivefiltering.paths import locate_file
import json
import laspy
import pdal
import tempfile
import numpy as np
from osgeo import gdal
import os


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
        """Calculate and save a meshgrid of the dataset with a custom resolution.

        :param filename:
            Filename to save the .tif. This can be a relative or absolute path.
            Relative paths are interpreted w.r.t. the current working directory.
        :type filename: str
        :param resolution:
            The resolution in meters used to calculate the mesh from the point cloud.
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

    def show_mesh(self, filename=None, resolution=2.0):
        """Load an existing . tif file or create a temporary file with a given resolution. The -tif is than visualised as a 3d mesh

        :param filename:
            optional filename to load a specific .tif file. The filename uses the same search method as the base class.
            A .tif ending must be used.
        :type filename: str
        :param resolution:
            The resolution in meters used to calculate the mesh from the point cloud.
        :type resolution: float

        :raises Warning: Raised if something other than a .tif file is selected.

        """

        # check if a filename is given, if not make a temporary tif file to view data
        if filename is None:
            print(
                "No geotif file was selected. A new temporary geotif file with a resolution of {} will be created but not saved.".format(
                    resolution
                )
            )
            # the temporary file is not removed automatically. Manual removal will be implemented
            with tempfile.NamedTemporaryFile(dir=os.getcwd()) as tmp_file:
                self.save_mesh(str(tmp_file.name), resolution=resolution)
                geo_tif_data = gdal.Open(str(tmp_file.name) + ".tif", gdal.GA_ReadOnly)
                os.remove(str(tmp_file.name) + ".tif")
        else:
            if os.path.splitext(filename)[1] == ".tif":
                filename = locate_file(filename)
                geo_tif_data = gdal.Open(filename, gdal.GA_ReadOnly)
            else:
                raise Warning("Please choose a .tif file")

        # use the number of x and y points to generate a grid.
        x = np.arange(0, geo_tif_data.RasterXSize)
        y = np.arange(0, geo_tif_data.RasterYSize)
        # get height information from
        band = geo_tif_data.GetRasterBand(1)
        z = band.ReadAsArray()
        return vis_mesh(x, y, z)

    def show(self):
        """Visualize the point cloud in Jupyter notebook

        Non-operational if called outside of Jupyter Notebook.
        """
        if len(self.data.x) >= self.warning_threshold:
            error_text = "Too many Datapoints loaded for visualisation.{} points are loaded, but only {} allowed".format(
                len(self.data.x), self.warning_threshold
            )
            raise ValueError(error_text)

        return vis_pointcloud(self.data.x, self.data.y, self.data.z)
