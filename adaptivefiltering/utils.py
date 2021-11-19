import collections
from os import pipe
from PIL import Image, ImageChops


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
    im = Image.open(path)
    bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    if bbox:
        im = im.crop(bbox)
        im.save(path)
