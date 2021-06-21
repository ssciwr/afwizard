from adaptivefiltering.visualization import vis_pointcloud
from adaptivefiltering.paths import locate_file

import laspy


class DataSet:
    def __init__(self, filename):
        """The main class that represents a Lidar data set.

        :param filename:
            Filename to load the dataset from. The dataset is expected to be in LAS/LAZ 1.2-1.4 format.
            If an absolute filename is given, the dataset is loaded from that location. Relative paths
            are interpreted (in this order) with respect to the directory set with :any:`set_data_directory`,
            the current working directory and the Python package installation directory.
        :type filename: str
        """
        filename = locate_file(filename)
        self.data = laspy.file.File(filename, mode="r")

    def show(self):
        """Visualize the point cloud in Jupyter notebook

        Non-operational if called outside of Jupyter Notebook.
        """
        return vis_pointcloud(self.data.x, self.data.y, self.data.z)
