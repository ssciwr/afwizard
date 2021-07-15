from adaptivefiltering.segmentation import Segment, Segmentation

import geojson
import os


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
    s2 = Segmentation.load(filename)

    assert geojson.dumps(s) == geojson.dumps(s2)
