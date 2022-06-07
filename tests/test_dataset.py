from afwizard.dataset import *
from afwizard.paths import get_temporary_filename
from afwizard.segmentation import Segmentation
from afwizard.asprs import asprs
from afwizard.pdal import PDALFilter
from afwizard.apps import assign_pipeline

import numpy as np
import os
import pytest


def test_show(dataset):
    # Test visualization - this is not actually very good in the absence of a display
    # But it helps in measuring coverage of the test suite.
    dataset.show(visualization_type="hillshade")
    dataset.show(visualization_type="hillshade", resolution=5.0)
    dataset.show(visualization_type="hillshade", classification=asprs(5))
    dataset.show(visualization_type="slope")
    dataset.show(visualization_type="slope", resolution=5.0)
    dataset.show(visualization_type="slope", classification=asprs(5))


def test_assign_pipeline(dataset, boundary_segmentation):

    f = PDALFilter(type="filters.smrf")
    # Create a pipeline from the filter
    pipeline = f.as_pipeline()
    with pytest.raises(AFwizardError):
        assign_pipeline(dataset, boundary_segmentation, [pipeline, pipeline])
    boundary_segmentation["features"][0]["properties"]["class"] = "A"

    assign_pipeline(dataset, boundary_segmentation, [pipeline, pipeline])


def test_restriction(dataset):
    # Trigger generation of the UI
    dataset.restrict()
    coordinates1 = [
        [
            [171.696546, -41.794334],
            [171.697361, -41.795342],
            [171.697319, -41.794206],
            [171.696546, -41.794334],
        ]
    ]
    coordinates2 = [
        [
            [171.696718, -41.79555],
            [171.698499, -41.79539],
            [171.69749, -41.795182],
            [171.696718, -41.79555],
        ]
    ]
    # Programmatically restrict with an artificial segment
    segmentation = Segmentation(
        [
            {
                "type": "Feature",
                "properties": {"style": {}},
                "geometry": {"type": "Polygon", "coordinates": coordinates1},
            },
        ],
        spatial_reference="EPSG:4326",
    )
    restricted = dataset.restrict(segmentation)
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
        ],
        spatial_reference="EPSG:4326",
    )
    restricted = dataset.restrict(segmentation)
    restricted.show()


def test_save_dataset(minimal_dataset):
    # This should do nothing
    minimal_dataset.save(minimal_dataset.filename)

    # Copy to another file
    tmpfile = get_temporary_filename("las")
    minimal_dataset.save(tmpfile)
    assert os.stat(tmpfile).st_size == os.stat(minimal_dataset.filename).st_size

    # Try doing that again without the override flag
    with pytest.raises(AFwizardError):
        minimal_dataset.save(tmpfile)

    # Now with the override flag
    minimal_dataset.save(tmpfile, overwrite=True)


def test_remove_classification(minimal_dataset):
    removed = remove_classification(minimal_dataset)
    vals = tuple(np.unique(removed.data["Classification"]))
    assert vals == (1,)


def test_reproject_dataset(dataset):
    from afwizard.dataset import reproject_dataset

    dataset2 = reproject_dataset(dataset, "EPSG:4362")

    # TODO: The following tests fail in CI with "ValueError: Iteration of zero-sized
    #       operands is not enabled" being thrown from PDAL. This is rather obscure.
    dataset3 = reproject_dataset(dataset2, "EPSG:25833 - ETRS89 / UTM zone 33N")
    dataset3 = reproject_dataset(
        dataset2, "EPSG:25833 - ETRS89 / UTM zone 33N", in_srs="EPSG:4362"
    )
