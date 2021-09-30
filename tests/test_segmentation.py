from adaptivefiltering.segmentation import Segment, Segmentation, InteractiveMap
from adaptivefiltering.dataset import DataSet
import geojson
import os
from . import dataset
import pytest


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


def test_show_map(dataset):
    # simple test to verify maps can be opened.

    segmentation_1 = Segmentation({"features": [], "type": "FeatureCollection"})
    segmentation_2 = Segmentation(
        [
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
    )
    test_map = InteractiveMap(dataset)
    test_map.show()
    test_map = InteractiveMap(segmentation=segmentation_2)
    test_map.show()
    # test segmentation as datatype
    with pytest.raises(TypeError):
        test_map = InteractiveMap(segmentation_2)

    with pytest.raises(Exception):
        test_map = InteractiveMap()
        test_map = InteractiveMap(segmentation_1)
        test_map = InteractiveMap(dataset, segmentation_1)
        test_map = InteractiveMap(dataset, segmentation_2)


def test_save_load_map_polygons(dataset):
    # initiate dataset and map
    test_map = InteractiveMap(dataset)

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
    assert test_map.return_polygon()["features"] == []

    # add polygons manually, check loading to the map
    # and check if they can be corretly returned

    test_map.draw_control.data = polygon_1
    test_map.load_polygon(Segmentation(polygon_2))
    returned_polygons = test_map.return_polygon()

    assert polygon_1[0] in returned_polygons["features"]
    assert polygon_2[0] in returned_polygons["features"]

    # make a second test map
    test_map_2 = InteractiveMap(dataset)
    # load the previously exportet polygons into the new map
    test_map_2.load_polygon(returned_polygons)
    assert test_map_2.return_polygon() == test_map.return_polygon()


def test_show_polygon_from_segmentation():
    segmentation_1 = Segmentation(
        [
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
    )
    segmentation_1.show()
