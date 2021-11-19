from adaptivefiltering.paths import load_schema
from adaptivefiltering.utils import convert_picture_to_base64, is_iterable, trim
from adaptivefiltering.dataset import DataSet
from adaptivefiltering.visualization import (
    hillshade_visualization,
    mesh_visualization,
    scatter_visualization,
    slopemap_visualization,
)
from adaptivefiltering.asprs import asprs
from adaptivefiltering.paths import get_temporary_filename
import geojson
import jsonschema
import ipyleaflet
import ipywidgets
import json
import numpy as np
import collections


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

        segmentation_map = InteractiveMap(segmentation=self)
        return segmentation_map.show()

    @property
    def __geo_interface__(self):
        return {
            "type": "FeatureCollection",
            "features": self.features,
        }


class Map:
    def __init__(self, dataset=None, segmentation=None, in_srs=None):
        """

        in_srs can be used to override the current srs.
        """

        from adaptivefiltering.pdal import PDALInMemoryDataSet
        from adaptivefiltering.dataset import reproject_dataset

        # handle exeptions
        if dataset and segmentation:
            raise Exception(
                "A dataset and a segmentation can't be loaded at the same time."
            )

        if dataset is None and segmentation["features"] is []:
            raise Exception("an empty segmention was given.")

        if dataset is None and segmentation is None:
            # if no dataset or segmentation is given, the map will be centered at the SSC office
            raise Exception(
                "Please use either a dataset or a segmentation. None were given."
            )

        # convert to pdal dataset
        dataset = PDALInMemoryDataSet.convert(dataset)

        # preserve the original srs
        if in_srs is None:
            self.original_srs = dataset.spatial_reference
        else:
            self.original_srs = in_srs

        # convert to a srs the ipyleaflet map can use.
        # the only way this seems to work is to convert the dataset to EPSG:4326 and set the map to expect EPSG:3857
        # https://gis.stackexchange.com/questions/48949/epsg-3857-or-4326-for-googlemaps-openstreetmap-and-leaflet/48952#48952
        self.dataset = reproject_dataset(dataset, "EPSG:4326", in_srs=self.original_srs)

        self.setup_map()
        self.setup_controls()

        # setup hs and slope variables

        self.hs_overlay = None
        self.hs_overlay_dict = {}
        self.slope_overlay_dict = {}

    def load_overlay(
        self,
        _type,
        classification=asprs[:],
        resolution=2,
        azimuth=315,
        angle_altitude=45,
        opacity=0.6,
    ):
        """
        Calculates either a hillshade or a slope map of the dataset and layers it ontop the satelite map.

        :param _type: Can either be "Hillshade" or "Slope"
        :type _type: String

        :param classification: a asprs classification that will be passed on to the visualisation function. Default = asprs[:]
        :type classification: asprs

        :param resolution:resolution for the visualisation. Default = 2
        :type resolution: int

        :param azimuth:azimuth for the visualisation. Default = 315
        :type azimuth: int

        :param angle_altitude: angle_altitude for the visualisation. Default = 45
        :type angle_altitude: int

        :param opacity: Sets the opacity of the layer, does not trigger recalculation of layers. Default = 0.6
        :type opacity: float

        """

        if _type != "Hillshade" and _type != "Slope":
            raise Exception("_type can only be 'Hillshade' or 'Slope'.")

        # set azimuth and angle_altitude to zero for _type =="Slope"
        # This makes it easer to find preexisting slope overlays
        if _type == "Slope":
            azimuth = 0
            angle_altitude = 0

        key_from_input = (
            "_type:"
            + _type
            + ",class:"
            + str(classification)
            + ",res:"
            + str(resolution)
            + ",az:"
            + str(azimuth)
            + ",ang:"
            + str(angle_altitude)
        )

        # if the dict is not empty, try to remove all layers present in the dict.
        if self.hs_overlay_dict != {}:
            for layer in self.hs_overlay_dict.values():
                if layer.name == type:
                    try:
                        self.map.remove_layer(layer)
                    except ipyleaflet.LayerException as e:
                        continue

        # if the desired hs is not already present, calculate it.
        # if it is, it will simply be loaded at the end of the function.
        if key_from_input not in self.hs_overlay_dict.keys():
            resolution = resolution * 0.00001 / 1.11  # approx formula

            # calculate the hillshade or slope
            if type == "Hillshade":
                canvas = hillshade_visualization(
                    self.dataset,
                    classification=classification,
                    resolution=resolution,
                    azimuth=azimuth,
                    angle_altitude=angle_altitude,
                )
            elif type == "Slope":
                canvas = slopemap_visualization(
                    self.dataset,
                    classification=classification,
                    resolution=resolution,
                )
            # setup a temporary filename for the picture.
            tmp_file = get_temporary_filename("png")

            # save figure with reduced whitespace
            canvas.figure.savefig(tmp_file, bbox_inches="tight", pad_inches=0, dpi=1200)
            # trim the remaining whitespace
            trim(tmp_file)
            # convert file to a base64 based url for ipyleaflet import
            tmp_url = convert_picture_to_base64(tmp_file)

            boundary_tuple = tuple(
                map(tuple, np.squeeze(self.rect_json["coordinates"]))
            )

            self.hs_overlay_dict[key_from_input] = ipyleaflet.ImageOverlay(
                url=tmp_url,
                bounds=(np.flip(boundary_tuple[0]), np.flip(boundary_tuple[2])),
                name=type,
            )
        # load the desired layer
        self.hs_overlay_dict[key_from_input].opacity = opacity
        self.map.add_layer(self.hs_overlay_dict[key_from_input])

    def show_map(self):
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

        # layer conrtol
        self.layer_control = ipyleaflet.LayersControl(position="topright")
        self.map.add_control(self.layer_control)

    def load_polygon(self, segmentation):
        """imports a segmentation object onto the map.
            The function also checks for doubles.

        :param segmentation:
            A segmentation object which is to be loaded.
        :type segmentation: Segmentation

        """

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

    def setup_map(self):
        """Takes the boundary coordinates of the  given dataset
        through the pdal hexbin filter and returns them as a segmentation.
        From the segmentation it calculates the center point as well as the edge points to implement the starting location of the map.
        The edge points are used to draw the boundary square of the given dataset.


        """
        from adaptivefiltering.pdal import execute_pdal_pipeline

        # execute the reprojection and hexbin filter.
        # this is nessesary for the map to function properly.
        hexbin_pipeline = execute_pdal_pipeline(
            dataset=self.dataset,
            config=[
                {
                    "type": "filters.hexbin",
                    "precision": 10,
                    "threshold": 1,
                    "sample_size": 10000,
                },
            ],
        )

        # get the coordinates from the metadata:
        # this gives us lat, lon but for geojson we need lon, lat
        boundary_json = json.loads(hexbin_pipeline.metadata)["metadata"][
            "filters.hexbin"
        ]["boundary_json"]

        boundary_coordinates = np.squeeze(boundary_json["coordinates"], axis=0)

        # get max and min values to set up square boundary
        # this should make it easier to preciscly fit the hillshade map
        min_x, max_x = min(np.asarray(boundary_coordinates)[:, 0]), max(
            np.asarray(boundary_coordinates)[:, 0]
        )
        min_y, max_y = min(np.asarray(boundary_coordinates)[:, 1]), max(
            np.asarray(boundary_coordinates)[:, 1]
        )

        self.rect_json = {
            "type": "Polygon",
            "coordinates": [
                [[min_x, min_y], [min_x, max_y], [max_x, max_y], [max_x, min_y]]
            ],
        }
        square_segmentation = Segmentation(
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
                            "fillColor": "#add8e6",
                            "fillOpacity": 0.1,
                            "clickable": True,
                        }
                    },
                    "geometry": self.rect_json,
                }
            ]
        )

        coordinates_mean = np.mean(np.squeeze(boundary_coordinates), axis=0)

        self.map = ipyleaflet.Map(
            basemap=ipyleaflet.basemaps.Esri.WorldImagery,
            center=(coordinates_mean[1], coordinates_mean[0]),
            # we have to use epsg 3857 see comment in init
            crs=ipyleaflet.projections.EPSG3857,
            scroll_wheel_zoom=False,
            max_zoom=20,
        )
        # add boundary marker
        self.map.add_layer(
            ipyleaflet.GeoJSON(data=square_segmentation, name="Boundary Square")
        )

    def return_polygon(self):
        """Exports the current polygon list as a Segmentation object

        :return:
            :param segmentation:
                All current polygons in one segmentation object
            :type segmentation: Segmentation


        """

        segmentation = Segmentation(self.draw_control.data)
        return segmentation


class InteractiveMap:
    def __init__(self, dataset=None, segmentation=None):
        """This class manages the interactive map on which one can choose the segmentation.
            It can be initilized with a dataset from which it will detect the boundaries and show them on the map.
            Or it can be initilized with a segmentation which will also be visualized on the map.
            There can be multiple polygons in the Segmentation and all will drawn. The


        :param dataset:
            The dataset from which the map should be displayed.
        :type dataset: Dataset
        :param segmentation:
            A premade segmentation can can be loaded and shown on a map without the need to load a dataset.
        :type segmentation: Segmentation

        """

        from adaptivefiltering.pdal import PDALInMemoryDataSet

        # handle exeptions
        if dataset and segmentation:
            raise Exception(
                "A dataset and a segmentation can't be loaded at the same time."
            )

        if dataset is None and segmentation["features"] is []:
            raise Exception("an empty segmention was given.")

        if dataset is None and segmentation is None:
            # if no dataset or segmentation is given, the map will be centered at the SSC office
            self.coordinates_mean = np.asarray([49.41745, 8.67529])
            self.segmentation = None

        if dataset is not None and not isinstance(dataset, DataSet):
            raise TypeError(
                "Dataset must be of type DataSet, but is " + str(type(dataset))
            )
        # prepare the map data

        # if a dataset is given the boundary of the data set is calculated via the hexbin function
        # and the in memory dataset is converted into EPSG:4326.
        if dataset and segmentation is None:
            self.segmentation = self.get_boundary(dataset)

        elif dataset is None and segmentation:
            self.segmentation = segmentation

        # setup ipyleaflet GeoJSON object
        boundary_coordinates = self.segmentation["features"][0]["geometry"][
            "coordinates"
        ]
        self.coordinates_mean = np.mean(np.squeeze(boundary_coordinates), axis=0)
        self.boundary_geoJSON = ipyleaflet.GeoJSON(data=self.segmentation)
        # for ipleaflet we need to change the order of the center coordinates

        self.m = ipyleaflet.Map(
            basemap=ipyleaflet.basemaps.Esri.WorldImagery,
            center=(self.coordinates_mean[1], self.coordinates_mean[0]),
            crs=ipyleaflet.projections.EPSG3857,
            scroll_wheel_zoom=True,
            max_zoom=20,
        )
        self.m.add_layer(self.boundary_geoJSON)

        # add polygon draw tool and zoom slider
        self.add_zoom_slider()
        self.add_polygon_control()

        # setup the grid with a list of widgets
        self.setup_grid([self.m])

    def get_boundary(self, dataset):
        """Takes the boundary coordinates of the  given dataset
            through the pdal hexbin filter and returns them as a segmentation.

        :param dataset:
            The dataset from which the map should be displayed.
        :type dataset: Dataset

        :return:
            hexbin_segmentation:
            The Segmentation of the area from the dataset
        :type hexbin_segmentation: Segmentation

        """
        from adaptivefiltering.pdal import execute_pdal_pipeline, PDALInMemoryDataSet

        # convert dataset to in memory pdal dataset
        dataset = PDALInMemoryDataSet.convert(dataset)

        # execute the reprojection and hexbin filter.
        # this is nessesary for the map to function properly.
        hexbin_pipeline = execute_pdal_pipeline(
            dataset=dataset,
            config=[
                {"type": "filters.hexbin"},
            ],
        )

        # get the coordinates from the metadata:
        # this gives us lat, lon but for geojson we need lon, lat
        coordinates = json.loads(hexbin_pipeline.metadata)["metadata"][
            "filters.hexbin"
        ]["boundary_json"]["coordinates"]

        # set up the segmentation object to later load into the map
        hexbin_segmentation = Segmentation(
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
                            "fillColor": "#add8e6",
                            "fillOpacity": 0.1,
                            "clickable": True,
                        }
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": coordinates,
                    },
                }
            ]
        )

        return hexbin_segmentation

    def add_zoom_slider(self):
        """Adds the zoom slider to the interactive map.
        Also sets the default zoom.
        """

        self.zoom_slider = ipywidgets.IntSlider(
            description="Zoom level:", min=0, max=20, value=16
        )
        ipywidgets.jslink((self.zoom_slider, "value"), (self.m, "zoom"))
        self.zoom_control1 = ipyleaflet.WidgetControl(
            widget=self.zoom_slider, position="topright"
        )
        self.m.add_control(self.zoom_control1)

    def add_polygon_control(self):
        """Adds the polygon draw control."""
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

        self.m.add_control(self.draw_control)

    def setup_grid(self, objects):
        """
        Setup the grid layout to allow the color bar and
        more on the right side of the map.
        """
        self.grid = ipywidgets.GridBox(
            children=objects,
            layout=ipywidgets.Layout(
                width="100%",
                grid_template_columns="70% 30%",
                grid_template_areas="""
                        "main sidebar "
                    """,
            ),
        )

    def return_polygon(self):
        """Exports the current polygon list as a Segmentation object

        :return:
            :param segmentation:
                All current polygons in one segmentation object
            :type segmentation: Segmentation


        """

        segmentation = Segmentation(self.draw_control.data)
        return segmentation

    def load_polygon(self, segmentation):
        """imports a segmentation object onto the map.
            The function also checks for doubles.

        :param segmentation:
            A segmentation object which is to be loaded.
        :type segmentation: Segmentation

        """

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

    def show(self):
        """This functions returns the grid object and makes the map visible.
        :param grid:
            The grid object which holds the map and the right side interface
        :type grid: ipyleaflet.grid
        """
        return self.grid
