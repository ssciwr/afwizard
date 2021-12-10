from adaptivefiltering.segmentation import (
    Segment,
    Segmentation,
    Map,
    get_min_max_values,
)
from adaptivefiltering.dataset import DataSet
from adaptivefiltering.utils import convert_Segmentation

import geojson
import os
from . import dataset, dataset_thingstaette
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


def test_convert_segmentation():
    test_json = {
        "features": [
            {
                "geometry": {
                    "coordinates": [
                        [
                            [8.705725083720136, 49.42308965603005],
                            [8.707155281693138, 49.423093286673364],
                            [8.70719283414031, 49.4231075567031],
                            [8.70718541147721, 49.4243549323965],
                            [8.706551800317948, 49.424360413763246],
                            [8.706526793019284, 49.42434617536664],
                            [8.706476609354468, 49.42434604799997],
                            [8.706451432959406, 49.42436015902981],
                            [8.705911958431617, 49.424358788345124],
                            [8.705886951319531, 49.424344549810485],
                            [8.705836767659251, 49.424344422166165],
                            [8.705799045163563, 49.42435850113913],
                            [8.70568638624683, 49.42431568966173],
                            [8.705680325255061, 49.424280236895314],
                            [8.705705501829526, 49.42426612603352],
                            [8.70566180317242, 49.424230577475726],
                            [8.705687064509279, 49.42420229189708],
                            [8.70566205754182, 49.4241880533137],
                            [8.705662651068081, 49.42408883026776],
                            [8.705687827549422, 49.42407471940917],
                            [8.705662820646415, 49.42406048082575],
                            [8.705688081894934, 49.42403219524591],
                            [8.705663075013408, 49.42401795666248],
                            [8.705663583745595, 49.42393290833498],
                            [8.705688844927863, 49.423904622754215],
                            [8.705745343422786, 49.42389767906303],
                            [8.705664007687247, 49.42386203472776],
                            [8.705664770778009, 49.42373446223257],
                            [8.705689947076984, 49.423720351372296],
                            [8.705665025140396, 49.42369193806687],
                            [8.705668501366063, 49.42311077443743],
                            [8.705725083720136, 49.42308965603005],
                        ]
                    ],
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
    test = Segmentation(test_json)
    test2 = convert_Segmentation(test, "EPSG:5243")
    test3 = convert_Segmentation(test2, "EPSG:4326", "EPSG:5243")
    test3_coord = np.asarray(test3["features"][0]["geometry"]["coordinates"])
    test_coord = np.asarray(test["features"][0]["geometry"]["coordinates"])
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

    test_seg_swapped = test_seg.swap_coordinates()
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


def test_show_map(dataset):
    # simple test to verify maps can be opened.

    test_map = Map(dataset)
    test_map.show_map()
    # todo setup test with segmentations.
    boundary_json = {
        "features": [
            {
                "geometry": {
                    "coordinates": [
                        [
                            [8.705725083720136, 49.42308965603005],
                            [8.707155281693138, 49.423093286673364],
                            [8.70719283414031, 49.4231075567031],
                            [8.70718541147721, 49.4243549323965],
                            [8.706551800317948, 49.424360413763246],
                            [8.706526793019284, 49.42434617536664],
                            [8.706476609354468, 49.42434604799997],
                            [8.706451432959406, 49.42436015902981],
                            [8.705911958431617, 49.424358788345124],
                            [8.705886951319531, 49.424344549810485],
                            [8.705836767659251, 49.424344422166165],
                            [8.705799045163563, 49.42435850113913],
                            [8.70568638624683, 49.42431568966173],
                            [8.705680325255061, 49.424280236895314],
                            [8.705705501829526, 49.42426612603352],
                            [8.70566180317242, 49.424230577475726],
                            [8.705687064509279, 49.42420229189708],
                            [8.70566205754182, 49.4241880533137],
                            [8.705662651068081, 49.42408883026776],
                            [8.705687827549422, 49.42407471940917],
                            [8.705662820646415, 49.42406048082575],
                            [8.705688081894934, 49.42403219524591],
                            [8.705663075013408, 49.42401795666248],
                            [8.705663583745595, 49.42393290833498],
                            [8.705688844927863, 49.423904622754215],
                            [8.705745343422786, 49.42389767906303],
                            [8.705664007687247, 49.42386203472776],
                            [8.705664770778009, 49.42373446223257],
                            [8.705689947076984, 49.423720351372296],
                            [8.705665025140396, 49.42369193806687],
                            [8.705668501366063, 49.42311077443743],
                            [8.705725083720136, 49.42308965603005],
                        ]
                    ],
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
    boundary_seg = Segmentation(boundary_json)
    test_map = Map(segmentation=boundary_seg)
    test_map.show_map()

    with pytest.raises(Exception):
        test_map = Map(dataset=dataset, segmentation=boundary_seg)
    with pytest.raises(Exception):
        test_map = Map()


def test_load_overlay(dataset_thingstaette):
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
