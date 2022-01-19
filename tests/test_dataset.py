from adaptivefiltering.dataset import *
from adaptivefiltering.paths import get_temporary_filename
from adaptivefiltering.segmentation import Segment, Segmentation
from adaptivefiltering.asprs import asprs

from . import dataset, minimal_dataset

import io
import numpy as np
import os
import pytest


def test_show(dataset):
    # Test visualization - this is not actually very good in the absence of a display
    # But it helps in measuring coverage of the test suite.
    dataset.show(visualization_type="hillshade")
    dataset.show(visualization_type="hillshade", resolution=5.0)
    dataset.show(visualization_type="hillshade", classification=asprs[5])
    dataset.show(visualization_type="slope")
    dataset.show(visualization_type="slope", resolution=5.0)
    dataset.show(visualization_type="slope", classification=asprs[5])


def test_restriction(minimal_dataset):
    # Trigger generation of the UI
    minimal_dataset.restrict()
    coordinates1 = [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]
    coordinates2 = [[0.2, 0.2], [0.4, 1.0], [1.0, 1.0], [1.0, 0.0], [0.2, 0.2]]
    # Programmatically restrict with an artificial segment
    segment = Segment(coordinates1)
    restricted = minimal_dataset.restrict(segment)
    restricted.show()

    # test for two polygons

    segmentation = Segmentation(
        [
            {
                "type": "Feature",
                "properties": {"style": {}},
                "geometry": {"type": "Polygon", "coordinates": coordinates1},
            },
            {
                "type": "Feature",
                "properties": {"style": {}},
                "geometry": {"type": "Polygon", "coordinates": coordinates2},
            },
        ]
    )
    restricted = minimal_dataset.restrict(segmentation)
    restricted.show()


def test_save_dataset(minimal_dataset):
    # This should do nothing
    minimal_dataset.save(minimal_dataset.filename)

    # Copy to another file
    tmpfile = get_temporary_filename()
    minimal_dataset.save(tmpfile)
    assert os.stat(tmpfile).st_size == os.stat(minimal_dataset.filename).st_size

    # Try doing that again without the override flag
    with pytest.raises(AdaptiveFilteringError):
        minimal_dataset.save(tmpfile)

    # Now with the override flag
    minimal_dataset.save(tmpfile, overwrite=True)


def test_remove_classification(minimal_dataset):
    removed = remove_classification(minimal_dataset)
    vals = tuple(np.unique(removed.data["Classification"]))
    assert vals == (1,)


def test_provenance(minimal_dataset):
    # For now, only check that output to a stream works
    with io.StringIO() as out:
        minimal_dataset.provenance(out)


def test_reproject_dataset(dataset):
    from adaptivefiltering.dataset import reproject_dataset

    dataset2 = reproject_dataset(dataset, "EPSG:4362")

    # TODO: The following tests fail in CI with "ValueError: Iteration of zero-sized
    #       operands is not enabled" being thrown from PDAL. This is rather obscure.
    dataset3 = reproject_dataset(dataset2, "EPSG:25833 - ETRS89 / UTM zone 33N")
    dataset3 = reproject_dataset(
        dataset2, "EPSG:25833 - ETRS89 / UTM zone 33N", in_srs="EPSG:4362"
    )
