from adaptivefiltering.asprs import asprs
from adaptivefiltering.paths import get_temporary_filename

from osgeo import gdal

import functools
import io
import IPython
import ipyvolume.pylab as vis
import ipywidgets
import numpy as np
import PIL

from matplotlib import cm


# Enable the matplotlib Jupyter backend
ipython = IPython.get_ipython()
if ipython is not None:
    ipython.magic("matplotlib widget")


def dispatch_visualization(dataset, visualization_type="hillshade", **options):
    visualization_functions = {
        "hillshade": hillshade_visualization,
        "mesh": mesh_visualization,
        "scatter": scatter_visualization,
        "slopemap": slopemap_visualization,
    }

    return visualization_functions[visualization_type](dataset, **options)


def gdal_object_to_inmemory_png(obj):
    # Encode it into an in-memory buffer
    img = PIL.Image.fromarray(obj.ReadAsArray())

    # Fix color scheme - also works for greyscale stuff
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Create and fill in-memory stream
    membuf = io.BytesIO()
    img.save(membuf, format="png")

    return membuf.getvalue()


def hillshade_visualization(dataset, azimuth=315, altitude=45):
    # Do the processing with GDAL
    gdal_img = gdal.DEMProcessing(
        get_temporary_filename(extension="png"),
        dataset.raster,
        "hillshade",
        azimuth=azimuth,
        altitude=altitude,
    )

    # Display it in an ipywidget
    return ipywidgets.Image(value=gdal_object_to_inmemory_png(gdal_img), format="png")


def slopemap_visualization(dataset):
    # Do the processing with GDAL
    gdal_img = gdal.DEMProcessing(
        get_temporary_filename(extension="tif"), dataset.raster, "slope"
    )

    # Display it in an ipywidget
    return ipywidgets.Image(value=gdal_object_to_inmemory_png(gdal_img), format="png")


def scatter_visualization(dataset, classification=asprs[:], threshold=1000000):
    # Convert to PDAL - this should go away when we make DEM's a first class citizen
    # of our abstractions
    from adaptivefiltering.pdal import PDALInMemoryDataSet

    dataset = PDALInMemoryDataSet.convert(dataset.dataset)

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

    return vis.gcc()


def mesh_visualization(dataset):
    data = dataset.raster

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

    return vis.gcc()
