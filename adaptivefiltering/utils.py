import collections
from os import pipe
from PIL import Image, ImageChops, ImageSequence
from io import BytesIO
from base64 import b64encode
import os


class AdaptiveFilteringError(Exception):
    pass


def is_iterable(object):
    return isinstance(object, collections.abc.Iterable) and not isinstance(object, str)


def stringify_value(value):
    """Stringify a value, making sequence space delimited"""
    if is_iterable(value):
        return " ".join(value)

    return str(value)


def trim(path):
    """Trim the whitespace around pictures from matplotlib"""

    im = Image.open(path)
    bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    if bbox:
        im = im.crop(bbox)
        im.save(path)


def convert_picture_to_base64(path):
    image = Image.open(path)
    ext = os.path.splitext(path)[1][1:]  # file extension
    f = BytesIO()
    image.save(f, ext)
    data = b64encode(f.getvalue())
    data = data.decode("ascii")
    url = "data:image/{};base64,".format(ext) + data
    return url
