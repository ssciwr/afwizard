from adaptivefiltering.paths import get_temporary_filename

from osgeo import gdal

import io
import ipywidgets
import PIL


def gdal_visualization(dataset, **options):
    # Do the processing with GDAL
    vis_type = options.pop("visualization_type")
    gdal_img = gdal.DEMProcessing(
        get_temporary_filename(extension="tif"), dataset.raster, vis_type, **options
    )

    # Encode it into an in-memory buffer
    img = PIL.Image.fromarray(gdal_img.ReadAsArray())

    # Fix color scheme - also works for greyscale stuff
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Create and fill in-memory stream
    membuf = io.BytesIO()
    img.save(membuf, format="png")

    return ipywidgets.Image(value=membuf.getvalue(), format="png")
