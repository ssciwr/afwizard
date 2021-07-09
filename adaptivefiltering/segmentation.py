from adaptivefiltering.paths import locate_schema

import geojson
import json
import jsonschema


class Segment:
    def __init__(self, polygon, metadata={}):
        self.polygon = geojson.MultiPolygon(polygon)
        self.metadata = metadata

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, _metadata):
        # Validate against our segment metadata schema
        with open(locate_schema("segment_metadata.json"), "r") as f:
            jsonschema.validate(instance=_metadata, schema=json.load(f))
        self._metadata = _metadata

    @property
    def __geo_interface__(self):
        return {
            "type": "Feature",
            "geometry": self.polygon,
            "properties": self.metadata,
        }


class Segmentation(geojson.FeatureCollection):
    @classmethod
    def load(cls, filename):
        """Load segmentation from a filename

        :param filename:
            The filename to load from. Relative paths are interpreted
            w.r.t. the current working directory.
        :type filename: str
        """
        raise NotImplementedError

    def save(self, filename):
        """Save the segmentation to disk

        :param filename:
            The filename to save the segmentation to. Relative paths are interpreted
            w.r.t. the current working directory.
        :type filename: str
        """
        raise NotImplementedError
