from adaptivefiltering.visualization import vis_pointcloud
from adaptivefiltering.paths import locate_file

import laspy


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

        filename = locate_file(filename)
        self.data = laspy.file.File(filename, mode="r")
        if len(self.data.x) >= self.warning_threshold:
            print(
                "This is a warning: {} points are loaded, but only {} can be displayed via the show() function".format(
                    len(self.data.x), self.warning_threshold
                )
            )

    def show(self, az=0, el=0):
        """Visualize the point cloud in Jupyter notebook

        Non-operational if called outside of Jupyter Notebook.
        """
        if len(self.data.x) >= self.warning_threshold:
            error_text = "Too many Datapoints loaded for visualisation.{} points are loaded, but only {} allowed".format(
                len(self.data.x), self.warning_threshold
            )
            raise ValueError(error_text)

        return vis_pointcloud(self.data.x, self.data.y, self.data.z, az, el)
