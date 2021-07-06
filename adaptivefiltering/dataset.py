from adaptivefiltering.paths import locate_file
from adaptivefiltering.segmentation import Segmentation
from adaptivefiltering.visualization import vis_pointcloud


import laspy
import sys


class DataSet:
    def __init__(self, filename):
        """The main class that represents a Lidar data set.

        :param filename:
            Filename to load the dataset from. The dataset is expected to be in LAS/LAZ 1.2-1.4 format.
            If an absolute filename is given, the dataset is loaded from that location. Relative paths
            are interpreted (in this order) with respect to the directory set with :any:`set_data_directory`,
            the current working directory, XDG data directories (Unix only) and the Python package
            installation directory.

        :type filename: str
        """
        filename = locate_file(filename)
        self.data = laspy.read(filename)

    def show(self, warning_threshold=750000):
        """Visualize the point cloud in Jupyter notebook
        Will give a warning if too many data points are present.
        Non-operational if called outside of Jupyter Notebook.
        """
        if len(self.data.x) >= warning_threshold:
            print(
                "This is a warning: {} points are loaded, but only {} can be displayed via the show() function".format(
                    len(self.data.x), warning_threshold
                )
            )
        else:
            return vis_pointcloud(self.data.x, self.data.y, self.data.z)

    def show_mesh(self, resolution=5.0):
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
        raise NotImplementedError

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
        raise NotImplementedError

    def save_mesh(self, filename, resolution=5.0):
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
        raise NotImplementedError

    def restrict(self, segmentation):
        """Restrict the data set to a spatial subset

        :param segmentation:
        :type: adaptivefiltering.segmentation.Segmentation
        """
        raise NotImplementedError

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
        raise NotImplementedError
