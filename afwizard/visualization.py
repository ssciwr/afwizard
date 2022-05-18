from afwizard.paths import get_temporary_filename

from osgeo import gdal
from PIL import Image

import io
import ipywidgets


def visualization_dispatcher(dataset, visualization_type=None, **options):
    """Dispatch to visualization implementations based on the visualization_type parameter"""
    # Dispatch by visualization type
    if visualization_type == "blended_hillshade_slope":
        return blended_hillshade_slope(dataset, **options)

    # By default, we treat this as a GDAL visualization type
    return gdal_visualization(dataset, visualization_type=visualization_type, **options)


def gdal_image(dataset, **options):
    """Create a GDAL visualization of a raster dataset"""
    # Do the processing with GDAL
    vis_type = options.pop("visualization_type")
    gdal_img = gdal.DEMProcessing(
        get_temporary_filename(extension="tif"), dataset.raster, vis_type, **options
    )

    # Encode it into an in-memory buffer
    img = Image.fromarray(gdal_img.ReadAsArray())

    # Fix color scheme - also works for greyscale stuff
    if img.mode != "RGB":
        img = img.convert("RGB")

    return img


def img_as_widget(img):
    """Create an image widget from a PIL.Image"""
    # Create and fill in-memory stream
    membuf = io.BytesIO()
    img.save(membuf, format="png")

    return ipywidgets.Image(value=membuf.getvalue(), format="png")


def gdal_visualization(dataset, **options):
    """Implement visualization using the GDAL DEM tool"""

    return img_as_widget(gdal_image(dataset, **options))


def blended_hillshade_slope(dataset, blending_factor=0.5, **hillshade_options):
    """Implemented blended hillshade/slopemap visualization"""
    # Create two images for hillshade and slopemap
    hillshade = gdal_image(dataset, visualization_type="hillshade", **hillshade_options)
    slopemap = gdal_image(dataset, visualization_type="slope")

    img = Image.blend(hillshade, slopemap, blending_factor)

    return img_as_widget(img)
