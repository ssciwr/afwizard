from adaptivefiltering.asprs import asprs
from adaptivefiltering.dataset import DataSet
from adaptivefiltering.paths import load_schema
from adaptivefiltering.utils import (
    is_iterable,
    convert_Segmentation,
)
from adaptivefiltering.utils import AdaptiveFilteringError
from adaptivefiltering.visualization import gdal_visualization

import base64
import geojson
import jsonschema
import ipyleaflet
import ipywidgets
import json
import numpy as np
import collections
import copy


class Segment:
    def __init__(self, polygon, metadata={}):
        self.polygon = geojson.Polygon(polygon)
        self.metadata = metadata

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, _metadata):
        # Validate against our segment metadata schema
        schema = load_schema("segment_metadata.json")
        jsonschema.validate(instance=_metadata, schema=schema)
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
    def load(cls, filename=None):
        """Load segmentation from a filename

        :param filename:
            The filename to load from. Relative paths are interpreted
            w.r.t. the current working directory.
        :type filename: str
        """

        if not isinstance(filename, collections.abc.Iterable):
            error = "filename needs to be a string, a list or a tuple, but is" + str(
                type(filename)
            )
            raise TypeError(error)

        # if a list of files is given a list of segmentations will be returned.
        if is_iterable(filename):
            segmentations = []
            for file in filename:
                with open(file, "r") as f:
                    segmentations.append(Segmentation(geojson.load(f)))
            return segmentations

        elif isinstance(filename, str):
            with open(filename, "r") as f:
                return Segmentation(geojson.load(f))

    def save(self, filename):
        """Save the segmentation to disk

        :param filename:
            The filename to save the segmentation to. Relative paths are interpreted
            w.r.t. the current working directory.
        :type filename: str
        """
        with open(filename, "w") as f:
            geojson.dump(self, f)

    def show(self):
        """This will create a new InteractiveMap with bounds from the segmentation.
             use
                 map = self.show()
                 map
             to show and access the data of the new map or just
                self.show() to show the map without interacting with it.
        :param grid:
             The grid object which holds the map and the right side interface
        :type grid: ipyleaflet.grid
        """

        segmentation_map = Map(segmentation=self)
        return segmentation_map.show()

    @property
    def __geo_interface__(self):
        return {
            "type": "FeatureCollection",
            "features": self.features,
        }


def get_min_max_values(segmentation):
    # goes over all features in the segmentation and return the min and max coordinates in a dict.
    min_max_dict = {"minX": [], "maxX": [], "minY": [], "maxY": []}
    for feature in segmentation["features"]:
        coord_array = np.asarray(feature["geometry"]["coordinates"])
        min_max_dict["minX"].append(np.min(coord_array, axis=1)[0, 0])
        min_max_dict["minY"].append(np.min(coord_array, axis=1)[0, 1])
        min_max_dict["maxX"].append(np.max(coord_array, axis=1)[0, 0])
        min_max_dict["maxY"].append(np.max(coord_array, axis=1)[0, 1])
    for key, value in min_max_dict.items():
        if "min" in key:
            min_max_dict[key] = min(value)
        elif "max" in key:
            min_max_dict[key] = max(value)

    return min_max_dict


def swap_coordinates(segmentation):
    new_features = copy.deepcopy(segmentation["features"])

    for feature, new_feature in zip(segmentation["features"], new_features):
        coord_array = np.asarray(feature["geometry"]["coordinates"])
        coord_array[:, :, [0, 1]] = coord_array[:, :, [1, 0]]
        new_feature["geometry"]["coordinates"] = coord_array.tolist()
    return Segmentation(new_features)


class Map:
    def __init__(self, dataset=None, segmentation=None, in_srs=None):
        """This class manages the interactive map on which one can choose the segmentation.
            It can be initilized with a dataset from which it will detect the boundaries and show them on the map.
            Or it can be initilized with a segmentation which will also be visualized on the map.
            There can be multiple polygons in the Segmentation and all will drawn. The
            depending on the segmentation it might be necessary to first swap the coordinates of the segmentation to fit with the ipyleaflet map
            in_srs can be used to override the current srs.


        :param dataset:
            The dataset from which the map should be displayed.
        :type dataset: Dataset
        :param segmentation:
            A premade segmentation can can be loaded and shown on a map without the need to load a dataset.
        :type segmentation: Segmentation
        :param in_srs:
            manually override the srs of the dataset or segmentation, necessary if none are specified in the object.
        :type in_srs: str

        """
        from adaptivefiltering.pdal import PDALInMemoryDataSet

        # handle exeptions
        if dataset and segmentation:
            raise AdaptiveFilteringError(
                "A dataset and a segmentation can't be loaded at the same time."
            )

        if dataset is None and segmentation["features"] is []:
            raise AdaptiveFilteringError("an empty segmention was given.")

        if dataset is None and segmentation is None:
            # if no dataset or segmentation is given, the map will be centered at the SSC office
            raise AdaptiveFilteringError(
                "Please use either a dataset or a segmentation. None were given."
            )

        # check if dataset and segmentation are of correct type
        if dataset:
            if isinstance(dataset, Segmentation):
                raise AdaptiveFilteringError(
                    "A segmentation was given as a dataset, please call Map(segmentation=yourSegmentation)"
                )
            elif not isinstance(dataset, DataSet):
                raise AdaptiveFilteringError(
                    f"The given dataset is not of type DataSet, but {type(dataset)}."
                )

        elif segmentation:
            if isinstance(segmentation, DataSet):
                raise AdaptiveFilteringError(
                    "A DataSet was given as a Segmentation, please call Map(dataset=yourDataset)"
                )
            elif not isinstance(segmentation, Segmentation):
                raise AdaptiveFilteringError(
                    f"The given segmentation is not of type Segmentation, but {type(segmentation)}."
                )

        # convert to pdal dataset
        if dataset:

            dataset = PDALInMemoryDataSet.convert(dataset)
            # preserve the original srs from dataset
            if in_srs is None:
                self.original_srs = dataset.spatial_reference
            else:
                if in_srs is None:
                    raise AdaptiveFilteringError(
                        "No srs could be found. Please specify one or use a dataset that includes one."
                    )
                self.original_srs = in_srs

        self.dataset = dataset  # needed for overlay function.

        # convert to a srs the ipyleaflet map can use.
        # the only way this seems to work is to convert the dataset to EPSG:4326 and set the map to expect EPSG:3857
        # https://gis.stackexchange.com/questions/48949/epsg-3857-or-4326-for-googlemaps-openstreetmap-and-leaflet/48952#48952
        boundary_segmentation = self.load_hexbin_boundary(dataset, segmentation)

        # get square edges of the boundary_segmentation for use in hillshade overlay
        self.boundary_edges = get_min_max_values(boundary_segmentation)

        self.setup_map(boundary_segmentation)
        self.setup_controls()

        # set up overlay dict.
        # this stores the parameters used in the load_overlay function to avoid multipole calculations of the same overlay

        self.overlay_dict = {}

    def load_overlay(
        self,
        map_type,
        classification=None,
        resolution=0.5,
        azimuth=315,
        altitude=30,
        opacity=0.6,
    ):
        """
        Calculates either a hillshade or a slope map of the dataset and layers it ontop the satelite map.
        stores the entered parameters in "overlay_dict" to ensure, that the overlays are not calculated, when already present.


        :param _type: Can either be "Hillshade" or "Slope"
        :type _type: String

        :param classification: a asprs classification that will be passed on to the visualisation function. Default = asprs[:]
        :type classification: asprs

        :param resolution:resolution for the visualisation. Default = 2
        :type resolution: int

        :param azimuth:azimuth for the visualisation. Default = 315
        :type azimuth: int

        :param altitude: angle altitude for the visualisation. Default = 45
        :type altitude: int

        :param opacity: Sets the opacity of the layer, does not trigger recalculation of layers. Default = 0.6
        :type opacity: float

        """

        # If no classification value was given, we use all classes
        if classification is None:
            classification = asprs[:]

        if self.dataset == None:
            raise AdaptiveFilteringError(
                "No dataset was given to calculate the hillshade or slope."
            )

        if map_type not in ("hillshade", "slope"):
            raise AdaptiveFilteringError(
                f"map_type can only be 'hillshade' or 'slope', not {map_type}"
            )

        # set azimuth and angle_altitude to zero for _type =="Slope"
        # This makes it easer to find preexisting slope overlays
        if map_type == "slope":
            azimuth = 0
            altitude = 0

        key_from_input = (
            "_type:"
            + map_type
            + ",class:"
            + str(classification)
            + ",res:"
            + str(resolution)
            + ",az:"
            + str(azimuth)
            + ",ang:"
            + str(altitude)
        )

        # if the dict is not empty, try to remove all layers present in the dict.
        for layer in self.overlay_dict.values():
            if layer.name == map_type:
                try:
                    self.map.remove_layer(layer)
                except ipyleaflet.LayerException as e:
                    continue

        # if the desired hs is not already present, calculate it.
        # if it is, it will simply be loaded at the end of the function.
        if key_from_input not in self.overlay_dict.keys():
            rastered = self.dataset.rasterize(
                classification=classification, resolution=resolution
            )

            # calculate the hillshade or slope
            if map_type == "hillshade":
                canvas = gdal_visualization(
                    rastered,
                    visualization_type="hillshade",
                    azimuth=azimuth,
                    altitude=altitude,
                )
            elif map_type == "slope":
                canvas = gdal_visualization(rastered, visualization_type="slope")

            # Construct URL for image to use in ipyleaflet
            data = base64.b64encode(canvas.value)
            data = data.decode("ascii")
            url = "data:image/{};base64,".format("png") + data

            # convert the edges into a tuple
            boundary_tuple = (
                (self.boundary_edges["minY"], self.boundary_edges["minX"]),
                (self.boundary_edges["maxY"], self.boundary_edges["maxX"]),
            )

            # save the overlay to the dict.
            self.overlay_dict[key_from_input] = ipyleaflet.ImageOverlay(
                url=url,
                bounds=((boundary_tuple[0]), (boundary_tuple[1])),
                rotation=90,
                name=map_type,
            )
        # load the desired layer
        self.overlay_dict[key_from_input].opacity = opacity
        self.map.add_layer(self.overlay_dict[key_from_input])

    def show(self):
        return self.map

    def setup_controls(self):
        """Modifies the polygon draw control to only include polygons, delete and clear all.
        Also initilizes the zoom slider, and layer control



        """
        self.draw_control = ipyleaflet.DrawControl(
            layout=ipywidgets.Layout(width="auto", grid_area="main")
        )
        # deactivate polyline and circlemarker
        self.draw_control.polyline = {}
        self.draw_control.circlemarker = {}

        self.draw_control.polygon = {
            "shapeOptions": {
                "fillColor": "black",
                "color": "black",
                "fillOpacity": 0.1,
            },
            "drawError": {"color": "#dd253b", "message": "Oups!"},
            "allowIntersection": False,
        }

        # add draw control
        self.map.add_control(self.draw_control)

        # add zoom control
        self.zoom_slider = ipywidgets.IntSlider(
            description="Zoom level:", min=0, max=20, value=16
        )
        ipywidgets.jslink((self.zoom_slider, "value"), (self.map, "zoom"))
        self.zoom_control1 = ipyleaflet.WidgetControl(
            widget=self.zoom_slider, position="topright"
        )
        self.map.add_control(self.zoom_control1)

        # layer control
        self.layer_control = ipyleaflet.LayersControl(position="topright")
        self.map.add_control(self.layer_control)

    def load_segmentation(self, segmentation):
        """imports a segmentation object onto the map.
            The function also checks for doubles.

        :param segmentation:
            A segmentation object which is to be loaded.
        :type segmentation: Segmentation

        """
        if isinstance(segmentation, str):
            segmentation = Segmentation.load(segmentation)

        # save current polygon data
        current_data = self.draw_control.data
        # filters only new polygons. to avoid double entrys. Ignores color and style, only checks for the geometry.
        new_polygons = [
            new_polygon
            for new_polygon in segmentation["features"]
            if not new_polygon["geometry"]
            in [data["geometry"] for data in current_data]
        ]
        # adds the new polygons to the current data
        new_data = current_data + new_polygons
        self.draw_control.data = new_data

    def load_hexbin_boundary(self, dataset=None, segmentation=None):
        """
        takes the dataset returns the boundary Segmentation.
        If a segmentation is given, this will convert it into a boundary segmentation.

        """
        from adaptivefiltering.pdal import execute_pdal_pipeline

        if dataset:
            info_pipeline = execute_pdal_pipeline(
                dataset=dataset, config=[{"type": "filters.info"}]
            )

            hexbin_pipeline = execute_pdal_pipeline(
                dataset=dataset,
                config=[
                    {
                        "type": "filters.hexbin",
                        "sample_size": json.loads(info_pipeline.metadata)["metadata"][
                            "filters.info"
                        ]["num_points"],
                        "precision": 10,
                        "threshold": 1,
                    },
                ],
            )

            # get the coordinates from the metadata:
            # this gives us lat, lon but for geojson we need lon, lat

            hexbin_coord = [
                json.loads(hexbin_pipeline.metadata)["metadata"]["filters.hexbin"][
                    "boundary_json"
                ]["coordinates"][0]
            ]
        elif segmentation:
            hexbin_coord = [
                features["geometry"]["coordinates"]
                for features in segmentation["features"]
            ][0]

        boundary_segmentation = Segmentation(
            [
                {
                    "type": "Feature",
                    "properties": {
                        "style": {
                            "stroke": True,
                            "color": "#add8e6",
                            "weight": 4,
                            "opacity": 0.5,
                            "fill": True,
                            "clickable": False,
                        }
                    },
                    "geometry": {"type": "Polygon", "coordinates": hexbin_coord},
                }
            ]
        )

        # the segmentation should already be in the correct format so no additaional conversion is requiered
        if dataset:

            boundary_segmentation = convert_Segmentation(
                boundary_segmentation, "EPSG:4326", self.original_srs
            )
            boundary_segmentation = swap_coordinates(boundary_segmentation)
        # add boundary marker
        return boundary_segmentation

    def setup_map(self, boundary_segmentation):
        """Takes the boundary coordinates of the  given dataset
        through the pdal hexbin filter and returns them as a segmentation.
        From the segmentation it calculates the center point as well as the edge points to implement the starting location of the map.
        The edge points are used to draw the boundary square of the given dataset.
        """
        from adaptivefiltering.pdal import execute_pdal_pipeline

        coordinates_mean = np.mean(
            np.squeeze(boundary_segmentation["features"][0]["geometry"]["coordinates"]),
            axis=0,
        )

        self.map = ipyleaflet.Map(
            basemap=ipyleaflet.basemaps.Esri.WorldImagery,
            center=(coordinates_mean[1], coordinates_mean[0]),
            # we have to use epsg 3857 see comment in init
            crs=ipyleaflet.projections.EPSG3857,
            scroll_wheel_zoom=False,
            max_zoom=20,
        )
        self.map.add_layer(
            ipyleaflet.GeoJSON(data=boundary_segmentation, name="Boundary")
        )

    def return_segmentation(self):
        """Exports the current polygon list as a Segmentation object

        :return:
            :param segmentation:
                All current polygons in one segmentation object
            :type segmentation: Segmentation


        """
        segmentation = Segmentation(self.draw_control.data)

        return segmentation
