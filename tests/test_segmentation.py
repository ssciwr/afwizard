from adaptivefiltering.segmentation import Segment, Segmentation

import geojson


def test_segmentation():
    # Create a random segment
    mp = geojson.utils.generate_random("MultiPolygon")

    # Assert that the metadata is validated and accessible
    segment = Segment(mp, metadata=dict(profile="Foobar"))
    assert segment.metadata["profile"] == "Foobar"

    # Use geojson serialization
    geojson.dumps(segment)

    # Instantiate a segmentation
    segmentation = Segmentation([segment])
    geojson.dumps(segmentation)
