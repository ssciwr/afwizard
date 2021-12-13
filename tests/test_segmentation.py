from adaptivefiltering.segmentation import (
    Segment,
    Segmentation,
    Map,
    get_min_max_values,
    swap_coordinates,
)
from adaptivefiltering.dataset import DataSet
from adaptivefiltering.utils import convert_Segmentation

import geojson
import os
from . import dataset, dataset_thingstaette, boundary_segmentation
import pytest
import numpy as np


def test_segmentation():
    # Create a random segment
    mp = geojson.utils.generate_random("Polygon")

    # Assert that the metadata is validated and accessible
    segment = Segment(mp, metadata=dict(profile="Foobar"))
    assert segment.metadata["profile"] == "Foobar"

    # Use geojson serialization
    geojson.dumps(segment)

    # Instantiate a segmentation
    segmentation = Segmentation([segment])
    geojson.dumps(segmentation)


def test_save_load_segmentation(tmpdir):
    p1 = geojson.utils.generate_random("Polygon")
    p2 = geojson.utils.generate_random("Polygon")

    s = Segmentation([Segment(p1), Segment(p2)])
    filename = os.path.join(tmpdir, "testsave.geojson")
    s.save(filename)
    s2 = Segmentation.load(filename=filename)
    s3 = Segmentation.load(filename=[filename, filename])
    s4 = Segmentation.load(filename=(filename, filename))
    with pytest.raises(TypeError):
        s5 = Segmentation.load(filename=4)

    assert geojson.dumps(s) == geojson.dumps(s2)


def test_convert_segmentation(boundary_segmentation):

    test2 = convert_Segmentation(boundary_segmentation, "EPSG:5243")
    test3 = convert_Segmentation(test2, "EPSG:4326", "EPSG:5243")
    test3_coord = np.asarray(test3["features"][0]["geometry"]["coordinates"])
    test_coord = np.asarray(
        boundary_segmentation["features"][0]["geometry"]["coordinates"]
    )
    assert (test3_coord - test_coord).all() < 1e-10


def test_swap_coordinates_segmentation():
    test_json = {
        "features": [
            {
                "geometry": {
                    "coordinates": [[[0, 1], [0, 1], [0, 1]]],
                    "type": "Polygon",
                },
                "properties": {
                    "style": {
                        "clickable": "false",
                        "color": "#add8e6",
                        "fill": "true",
                        "opacity": 0.5,
                        "stroke": "true",
                        "weight": 4,
                    }
                },
                "type": "Feature",
            }
        ],
        "type": "FeatureCollection",
    }
    test_seg = Segmentation(test_json)

    test_seg_swapped = swap_coordinates(test_seg)
    assert test_seg_swapped["features"][0]["geometry"]["coordinates"] == [
        [[1, 0], [1, 0], [1, 0]]
    ]


def test_get_min_max_values():
    test_json = {
        "features": [
            {
                "geometry": {
                    "coordinates": [[[0, 3], [1, 1], [4, 1]]],
                    "type": "Polygon",
                },
                "properties": {
                    "style": {
                        "clickable": "false",
                        "color": "#add8e6",
                        "fill": "true",
                        "opacity": 0.5,
                        "stroke": "true",
                        "weight": 4,
                    }
                },
                "type": "Feature",
            }
        ],
        "type": "FeatureCollection",
    }
    test_seg = Segmentation(test_json)
    assert get_min_max_values(test_seg) == {"minX": 0, "maxX": 4, "minY": 1, "maxY": 3}


def test_show_map(dataset, boundary_segmentation):
    # simple test to verify maps can be opened.

    test_map = Map(dataset)
    test_map.show()
    # todo setup test with segmentations.

    test_map = Map(segmentation=boundary_segmentation)
    test_map.show()

    with pytest.raises(Exception):
        test_map = Map(dataset=dataset, segmentation=boundary_segmentation)
        test_map = Map()

        test_map = Map(dataset=boundary_segmentation)
        test_map = Map(dataset=5)

        test_map = Map(segmentation=dataset)
        test_map = Map(segmentation=5)


def test_load_overlay(dataset_thingstaette, boundary_segmentation):
    test_map = Map(dataset_thingstaette)
    # first overlay
    test_map.load_overlay("Hillshade", resolution=5)
    test_map.load_overlay("Slope", resolution=2, opacity=0.5)
    # second overlay
    test_map.load_overlay("Hillshade", resolution=4, opacity=1)
    test_map.load_overlay("Slope", resolution=1, opacity=0.6)
    # return to first overlay with different opacity
    test_map.load_overlay("Hillshade", resolution=5, opacity=0.1)
    test_map.load_overlay("Slope", resolution=2, opacity=0.1)
    test_map2 = Map(segmentation=boundary_segmentation)
    with pytest.raises(Exception):
        test_map2.load_overlay()


def test_save_load_map_polygons(dataset):
    # initiate dataset and map
    test_map = Map(dataset)

    # create two example polygons
    polygon_1 = [
        {
            "type": "Feature",
            "properties": {
                "style": {
                    "stroke": True,
                    "color": "black",
                    "weight": 4,
                    "opacity": 0.5,
                    "fill": True,
                    "fillColor": "black",
                    "fillOpacity": 0.1,
                    "clickable": True,
                }
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [171.715394, -41.792157],
                        [171.710101, -41.802235],
                        [171.728054, -41.800635],
                        [171.715394, -41.792157],
                    ]
                ],
            },
        }
    ]

    polygon_2 = [
        {
            "type": "Feature",
            "properties": {
                "style": {
                    "stroke": True,
                    "color": "black",
                    "weight": 4,
                    "opacity": 0.5,
                    "fill": True,
                    "fillColor": "black",
                    "fillOpacity": 0.1,
                    "clickable": True,
                }
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [171.715394, -41.792157],
                        [171.710101, -41.802235],
                        [171.728054, -41.800635],
                        [171.715394, -41.792157],
                    ]
                ],
            },
        }
    ]
    # check if empty Segmentation can be returend
    assert test_map.return_segmentation()["features"] == []

    # add polygons manually, check loading to the map
    # and check if they can be corretly returned

    test_map.draw_control.data = polygon_1
    test_map.load_segmentation(Segmentation(polygon_2))
    returned_polygons = test_map.return_segmentation()

    assert polygon_1[0] in returned_polygons["features"]
    assert polygon_2[0] in returned_polygons["features"]

    # make a second test map
    test_map_2 = Map(dataset)
    # load the previously exportet polygons into the new map
    test_map_2.load_segmentation(returned_polygons)
    assert test_map_2.return_segmentation() == test_map.return_segmentation()


def test_show_polygon_from_segmentation(boundary_segmentation):
    boundary_segmentation.show()
