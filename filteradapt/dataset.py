from filteradapt.visualization import vis_pointcloud
from filteradapt.paths import locate_file

import laspy


class DataSet:
    def __init__(self, filename):
        """DataSet Init

        Args:
            filename ([type]): [description]
        """
        filename = locate_file(filename)
        self.data = laspy.file.File(filename, mode="r")

    def show(self, **kwargs):
        """takes the data set and plots it in an interactive graph.

        Returns:
            [vis.figure]: Graph object of the pointcloud
        """
        return vis_pointcloud(self.data.x, self.data.y, self.data.z, **kwargs)
