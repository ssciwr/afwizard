from adaptivefiltering.asprs import asprs

import functools
import IPython
import ipyvolume.pylab as vis
import matplotlib.pyplot as plt
import numpy as np
import richdem
import tempfile

from matplotlib import cm


# Enable the matplotlib Jupyter backend
ipython = IPython.get_ipython()
if ipython is not None:
    ipython.magic("matplotlib widget")


def hillshade_visualization(
    dataset, classification=asprs[:], resolution=1.0, azimuth=315, angle_altitude=45
):
    # Convert to PDAL - this should go away when we make DEM's a first class citizen
    # of our abstractions
    from adaptivefiltering.pdal import PDALInMemoryDataSet

    dataset = PDALInMemoryDataSet.convert(dataset)

    # Make a temporary tif file to view data
    if (resolution, classification) not in dataset._mesh_data_cache:
        # Write a temporary file
        with tempfile.NamedTemporaryFile() as tmp_file:
            dataset.save_mesh(
                str(tmp_file.name),
                resolution=resolution,
                classification=classification,
            )

    # Retrieve the raster data from cache
    data = dataset._mesh_data_cache[resolution, classification]
    band = data.GetRasterBand(1)
    z = band.ReadAsArray()

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


def slopemap_visualization(dataset, classification=asprs[:], resolution=1.0):
    # Convert to PDAL - this should go away when we make DEM's a first class citizen
    # of our abstractions
    from adaptivefiltering.pdal import PDALInMemoryDataSet

    dataset = PDALInMemoryDataSet.convert(dataset)

    # make a temporary tif file to view data
    with tempfile.NamedTemporaryFile() as tmp_file:
        dataset.save_mesh(
            str(tmp_file.name),
            resolution=resolution,
            classification=classification,
        )
        shasta_dem = richdem.LoadGDAL(tmp_file.name + ".tif")

    # Have richdem calculate the slope map
    slope = richdem.TerrainAttribute(shasta_dem, attrib="slope_riserun")

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


def scatter_visualization(dataset, classification=asprs[:], threshold=1000000):
    # Convert to PDAL - this should go away when we make DEM's a first class citizen
    # of our abstractions
    from adaptivefiltering.pdal import PDALInMemoryDataSet

    dataset = PDALInMemoryDataSet.convert(dataset)

    if len(dataset.data["X"]) >= threshold:
        raise ValueError(
            f"Too many Datapoints loaded for visualisation.{len(dataset.data['X'])} points are loaded, but only {threshold} allowed"
        )

    # Filter classification data - could also be done with PDAL
    filtered_data = dataset.data[
        functools.reduce(
            np.logical_or,
            (dataset.data["Classification"] == c for c in classification),
        )
    ]

    # Extract coordinate arrays
    x = np.asarray(filtered_data["X"])
    y = np.asarray(filtered_data["Y"])
    z = np.asarray(filtered_data["Z"])

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


def mesh_visualization(dataset, classification=asprs[:], resolution=1.0):
    # Convert to PDAL - this should go away when we make DEM's a first class citizen
    # of our abstractions
    from adaptivefiltering.pdal import PDALInMemoryDataSet

    dataset = PDALInMemoryDataSet.convert(dataset)

    # make a temporary tif file to view data
    if (resolution, classification) not in dataset._mesh_data_cache:
        # Write a temporary file
        with tempfile.NamedTemporaryFile() as tmp_file:
            dataset.save_mesh(
                str(tmp_file.name),
                resolution=resolution,
                classification=classification,
            )

    # Retrieve the raster data from cache
    data = dataset._mesh_data_cache[resolution, classification]

    # use the number of x and y points to generate a grid.
    x = np.arange(0, data.RasterXSize)
    y = np.arange(0, data.RasterYSize)

    # multiply x and y with the given resolution for comparable plot.
    x = x * data.GetGeoTransform()[1]
    y = y * data.GetGeoTransform()[1]

    # get height information from
    band = data.GetRasterBand(1)
    z = band.ReadAsArray()

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
