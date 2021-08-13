import ipyvolume.pylab as vis
import matplotlib.pyplot as plt
import mpld3
import numpy as np

from matplotlib import cm
import richdem as rd


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
    # Enable interactive elements on matplotlib plots. Ignoring the
    # resulting errors if being called outside of notebooks.
    try:
        mpld3.enable_notebook()
    except AttributeError:
        pass

    # For future reference: This is how several hillshades can share the
    # zoom: https://stackoverflow.com/questions/4200586/matplotlib-pyplot-how-to-zoom-subplots-together

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

    # Do the visualization with matplotlib. The interactive elements
    # are automatically added by mpld3.
    plt.imshow(hs_array, cmap=cm.gray)
    plt.show()


def vis_slope(slope):
    """Visualize a hillshade model in Jupyter Notebook

    :param slope:
        richdem slope object GeoTiff export.
    :type z: richdem.rdarray
    """

    try:
        mpld3.enable_notebook()
    except AttributeError:
        pass

    rd.rdShow(slope, axes=False, cmap="magma", figsize=(8, 5.5))
    plt.show()
