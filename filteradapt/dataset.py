from filteradapt.visualization import vis_pointcloud
from filteradapt.paths import locate_file

import laspy


class DataSet:
    def __init__(self, filename=None):
        filename = locate_file(filename)
        self.data = laspy.file.File(filename, mode="r")

    def show(self, **kwargs):
        return vis_pointcloud(self.data.x, self.data.y, self.data.z, **kwargs)
