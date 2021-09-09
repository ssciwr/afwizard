import IPython
import ipyvolume.pylab as vis
import matplotlib.pyplot as plt, mpld3
import numpy as np

from matplotlib import cm
import richdem as rd


# Enable the matplotlib Jupyter backend
ipython = IPython.get_ipython()
if ipython is not None:
    ipython.magic("matplotlib widget")


def vis_pointcloud(x, y, z):
    """Visualization of a point cloud in Jupyter notebooks

    :param x: The array x-coordinates of the point cloud
    :param y: The array y-coordinates of the point cloud
    :param z: The array z-coordinates of the point cloud
    :type x: numpy.array
    :type y: numpy.array
    :type z: numpy.array
    """
    # laspy.read() gives the x,y and z coordinates as a special datatype "laspy.point.dims.ScaledArrayView"
    # this data type is not compatible with the ipyvolume plot, thus all coordinates are converted to numpy arrays before plotting.

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

    X, Y = np.meshgrid(x, y)

    # define the color map
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


def vis_hillshade(z):
    """Visualize a hillshade model in Jupyter Notebook

    :param z:
        The z-coordinates on a given raster produced by e.g.
        GeoTiff export.
    :type z: numpy.array
    """
    # These two values might be worth exposing
    azimuth = 315
    angle_altitude = 45

    # Calculcate the hillshade values. Code taken from here
    # http://rnovitsky.blogspot.com/2010/04/using-hillshade-image-as-intensity.html
    x, y = np.gradient(z)
    slope = 0.5 * np.pi - np.arctan(np.sqrt(x * x + y * y))
    aspect = np.arctan2(-x, y)
    azimuthrad = azimuth * np.pi / 180.0
    altituderad = angle_altitude * np.pi / 180.0
    shaded = np.sin(altituderad) * np.sin(slope) + np.cos(altituderad) * np.cos(
        slope
    ) * np.cos(azimuthrad - aspect)
    hs_array = 255 * (shaded + 1) / 2

    # Plot the image
    plt.ioff()
    fig, ax = plt.subplots()
    ax.imshow(hs_array, cmap=cm.gray)

    # Make sure that we get the "raw" image and no axes, whitespace etc.
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    fig.set_tight_layout(True)

    # Set some properties on the canvas that fit our use case
    fig.canvas.toolbar_visible = False
    fig.canvas.header_visible = False
    fig.canvas.footer_visible = False
    fig.canvas.resizable = False
    fig.canvas.capture_scroll = False

    # Return the figure object. The widget can be extracted from this using
    # the canvas property
    return fig


def vis_slope(slope):
    """Visualize a slope model in Jupyter Notebook

    :param slope:
        richdem slope object GeoTiff export.
    :type z: richdem.rdarray
    """

    # Plot the image
    plt.ioff()
    fig, ax = plt.subplots()
    # colour is subject to change and discussion.
    ax.imshow(slope, cmap=cm.RdBu)

    # Make sure that we get the "raw" image and no axes, whitespace etc.
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    fig.set_tight_layout(True)

    # Set some properties on the canvas that fit our use case
    fig.canvas.toolbar_visible = False
    fig.canvas.header_visible = False
    fig.canvas.footer_visible = False
    fig.canvas.resizable = False
    fig.canvas.capture_scroll = False

    # Return the figure object. The widget can be extracted from this using
    # the canvas property
    return fig
