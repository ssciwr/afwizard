import ipyvolume.pylab as vis
import numpy as np
from matplotlib import cm


def vis_pointcloud(x, y, z):
    """Visualization of a point cloud in Jupyter notebooks

    :param x: The array x-coordinates of the point cloud
    :param y: The array y-coordinates of the point cloud
    :param z: The array z-coordinates of the point cloud
    :type x: numpy.array
    :type y: numpy.array
    :type z: numpy.array
    """

    # converting to numpy array solves the IndexType error.

    x = np.asarray(x)
    y = np.asarray(y)
    z = np.asarray(z)

    fig = vis.figure(width=1000)
    vis.scatter(
        x,
        y,
        z,
        color="red",
        size=0.05,
    )
    vis.style.box_off()
    vis.view(azimuth=180, elevation=90)
    fig.xlim = (min(x), max(x))
    fig.ylim = (min(y), max(y))
    fig.zlim = (min(z), max(z))
    vis.show()


def vis_mesh(x, y, z):
    """Visualization of a point cloud in Jupyter notebooks

    :param x: The array x-coordinates of the point cloud
    :param y: The array y-coordinates of the point cloud
    :param z: The array z-coordinates of the point cloud
    :type x: numpy.array
    :type y: numpy.array
    :type z: numpy.array
    """

    # converting to numpy array solves the IndexType error.

    X, Y = np.meshgrid(x, y)

    # define the color maü
    colormap = cm.terrain
    znorm = z / (np.max(z) + 100)
    znorm.min(), znorm.max()
    color = colormap(znorm)

    fig = vis.figure(width=1000)
    vis.plot_surface(X, Y, z, color=color[..., :3])
    vis.style.box_off()
    vis.view(azimuth=0, elevation=-90)
    fig.xlim = (np.min(x), np.max(x))
    fig.ylim = (np.min(y), np.max(y))
    fig.zlim = (np.min(z), np.max(z))
    vis.show()
