from adaptivefiltering.asprs import asprs_class_name
from adaptivefiltering.dataset import DataSet, DigitalSurfaceModel, reproject_dataset
from adaptivefiltering.filter import Pipeline, Filter, update_data
from adaptivefiltering.library import (
    get_filter_libraries,
    library_keywords,
)
from adaptivefiltering.paths import load_schema, within_temporary_workspace
from adaptivefiltering.pdal import PDALInMemoryDataSet
from adaptivefiltering.segmentation import Map, Segmentation
from adaptivefiltering.utils import AdaptiveFilteringError
from adaptivefiltering.widgets import WidgetFormWithLabels

import collections
import contextlib
import copy
import ipywidgets
import ipywidgets_jsonschema
import IPython
import itertools
import numpy as np
import pyrsistent
import pytools
import wrapt
from ipyleaflet import Marker
import functools


fullwidth = ipywidgets.Layout(width="100%")


def return_proxy(creator, widget):
    # Create a new proxy object by calling the creator once
    proxy = wrapt.ObjectProxy(creator())

    # Define a handler that updates the proxy
    def _update_proxy(_):
        proxy.__wrapped__ = creator()

    # Register handler that triggers proxy update
    widget.observe(
        _update_proxy, names=("value", "selected_index", "data"), type="change"
    )

    return proxy


@contextlib.contextmanager
def hourglass_icon(button):
    """Context manager to temporarily show an hourglass icon on a button

    :param button: The button
    :type button: ipywidgets.Button
    """
    button.icon = "hourglass-half"
    yield
    button.icon = ""


def as_pdal(dataset):
    """Transform a dataset or digital surface model into a PDAL dataset"""
    if isinstance(dataset, DigitalSurfaceModel):
        return as_pdal(dataset.dataset)
    return PDALInMemoryDataSet.convert(dataset)


def classification_widget(datasets, selected=None):
    """Create a widget to select classification values

    The shown classification values are taken from the datasets themselves
    and the total amount of points for each class is shown in the widget.
    The widget then allows to select an arbitrary number of classes. By default,
    all classes are selected, unless ground points are present in the datasets
    in which case only these are selected.

    :param datasets:
        A list of datasets.
    :type datasets: list
    :param selected:
        An optional list of pre-selected indices.
    :type selected: list
    """

    # Determine classes present across all datasets
    joined_count = {}
    for dataset in datasets:
        # Make sure that we have an in-memory copy of the dataset
        dataset = as_pdal(dataset)

        # Get the lists present in this dataset
        for code, numpoints in enumerate(np.bincount(dataset.data["Classification"])):
            if numpoints > 0:
                joined_count.setdefault(code, 0)
                joined_count[code] += numpoints

    # If the dataset already contains ground points, we only want to use
    # them by default. This saves tedious work for the user who is interested
    # in ground point filtering results.
    if selected is None:
        if 2 in joined_count:
            selected = [2]
        else:
            # If there are no ground points, we use all classes
            selected = list(joined_count.keys())

    return ipywidgets.SelectMultiple(
        options=[
            (f"[{code}]: {asprs_class_name(code)} ({joined_count[code]} points)", code)
            for code in sorted(joined_count.keys())
        ],
        value=selected,
    )


@pytools.memoize(key=lambda d, p, **c: (d, p.config, pyrsistent.pmap(c)))
def cached_pipeline_application(dataset, pipeline, **config):
    """Call filter pipelinex execution in a cached way"""
    return pipeline.execute(dataset, **config)


def expand_variability_string(varlist, type_="string", samples_for_continuous=5):
    """Split a string into variants allowing comma separation and ranges with dashes

    :param varlist:
        The input string to expand
    :type varlist: str
    :param type_:
        The type of the variables to return. Maybe `string`, `integer` or `number`.
    :type type_: str
    :param samples_for_continuous:
        The number of samples to use when resolving ranges of floating point values (defaults to 5)
    :type samples_for_continuous: int
    """
    # For discrete variation, we use comma separation
    for part in varlist.split(","):
        part = part.strip()

        # If this is a numeric parameter it might also have ranges specified by dashes
        if type_ == "number":
            range_ = part.split("-")

            if len(range_) == 1:
                yield float(part)

            # If a range was found we handle this
            if len(range_) == 2:
                for i in range(samples_for_continuous):
                    yield float(range_[0]) + i / (samples_for_continuous - 1) * (
                        float(range_[1]) - float(range_[0])
                    )

            # Check for weird patterns like "0-5-10"
            if len(range_) > 2:
                raise ValueError(f"Given an invalid range of parameters: '{part}'")

        if type_ == "integer":
            range_ = part.split("-")

            if len(range_) == 1:
                yield int(part)

            if len(range_) == 2:
                if type_ == "integer":
                    for i in range(int(range_[0]), int(range_[1]) + 1):
                        yield i

            if len(range_) > 2:
                raise ValueError(f"Given an invalid range of parameters: '{part}'")

        if type_ == "string":
            yield part


def create_variability(batchdata, samples_for_continuous=5, non_persist_only=True):
    """Create combinatorical product of specified variants

    :param batchdata:
        The variability data provided by the filter data model.
    :type batchdata: list
    :param samples_for_continuous:
        The number of samples to use when resolving ranges of floating point values (defaults to 5)
    :type samples_for_continuous: int
    :param non_persist_only:
        Whether or not the creation of variability is restricted to entries
        with `persist=False`. The `persist` field is used to distinguish batch
        processing from end user configuration.
    :type non_persist_only: bool
    """
    if non_persist_only:
        batchdata = [bd for bd in batchdata if not bd["persist"]]

    variants = []
    varpoints = [
        tuple(
            expand_variability_string(
                bd["values"],
                samples_for_continuous=samples_for_continuous,
                type_=bd["type"],
            )
        )
        for bd in batchdata
    ]
    for combo in itertools.product(*varpoints):
        variant = []
        for i, val in enumerate(combo):
            newbd = batchdata[i].copy()
            newbd["values"] = val
            variant.append(newbd)
        variants.append(variant)

    return variants


# A data structure to store widgets within to quickly navigate back and forth
# between visualizations in the pipeline_tuning widget.
PipelineWidgetState = collections.namedtuple(
    "PipelineWidgetState",
    ["pipeline", "rasterization", "visualization", "classification", "image"],
)


def pipeline_tuning(datasets=[], pipeline=None):
    """The Jupyter UI to create a filtering pipeline from scratch.

    The use of this UI is described in detail in `the notebook on creating filter pipelines`_.

    .. _the notebook on creating filter pipelines: filtering.nblink

    :param datasets:
        One or more instances of Lidar datasets to work on
    :type datasets: list
    :param pipeline:
        A pipeline to use as a starting point. If omitted, a new pipeline object will be created.
    :type pipeline: adaptivefiltering.filter.Pipeline
    :return:
        Returns the created pipeline object
    :rtype: adaptivefiltering.filter.Pipeline
    """

    # Instantiate a new pipeline object if we are not modifying an existing one.
    if pipeline is None:
        pipeline = Pipeline()

    # If a single dataset was given, transform it into a list
    if isinstance(datasets, DataSet):
        datasets = [datasets]

    # Assert that at least one dataset has been provided
    if len(datasets) == 0:
        raise AdaptiveFilteringError(
            "At least one dataset must be provided to pipeline_tuning"
        )

    # Create the data structure to store the history of visualizations in this app
    history = []

    # Loop over the given datasets
    def create_history_item(ds, data, classes=None):
        # Create a new classification widget and insert it into the Box
        _class_widget = classification_widget([ds], selected=classes)
        app.right_sidebar.children[-1].children = (_class_widget,)

        # Create widgets from the datasets
        image = ipywidgets.Box(
            children=[
                ds.show(
                    classification=class_widget.children[0].value,
                    **rasterization_widget_form.data,
                    **visualization_form.data,
                )
            ]
        )

        # Add the set of widgets to our history
        history.append(
            PipelineWidgetState(
                pipeline=data,
                rasterization=rasterization_widget_form.data,
                visualization=visualization_form.data,
                classification=_class_widget,
                image=image,
            )
        )

        # Add it to the center Tab widget
        nonlocal center
        index = len(center.children)
        center.children = center.children + (image,)
        center.titles = center.titles + (f"#{index}",)

    # Configure control buttons
    preview = ipywidgets.Button(description="Preview", layout=fullwidth)
    finalize = ipywidgets.Button(description="Finalize", layout=fullwidth)
    delete = ipywidgets.Button(
        description="Delete this filtering", layout=ipywidgets.Layout(width="50%")
    )
    delete_all = ipywidgets.Button(
        description="Delete filtering history", layout=ipywidgets.Layout(width="50%")
    )

    # The center widget holds the Tab widget to browse history
    center = ipywidgets.Tab(children=[], titles=[])
    center.layout = fullwidth

    def _switch_tab(_):
        if len(center.children) > 0:
            item = history[center.selected_index]
            pipeline_form.data = item.pipeline
            rasterization_widget_form.data = item.rasterization
            visualization_form_widget.data = item.visualization
            classification_widget.children = (item.classification,)

    def _trigger_preview(config=None):
        if config is None:
            config = pipeline_form.data

        # Extract the currently selected classes and implement heuristic:
        # If ground was already in the classification, we keep the values
        if history:
            old_classes = history[-1].classification.value
            had_ground = 2 in [o[1] for o in history[-1].classification.options]
            classes = old_classes if had_ground else None
        else:
            classes = None

        for ds in datasets:
            # Extract the pipeline from the widget
            nonlocal pipeline
            pipeline = pipeline.copy(**config)

            # TODO: Do this in parallel!
            with within_temporary_workspace():
                transformed = cached_pipeline_application(ds, pipeline)

            # Create a new entry in the history list
            create_history_item(transformed, config, classes=classes)

            # Select the newly added tab
            center.selected_index = len(center.children) - 1

    def _update_preview(button):
        with hourglass_icon(button):
            # Check whether there is batch-processing information
            batchdata = pipeline_form.batchdata

            if len(batchdata) == 0:
                _trigger_preview()
            else:
                for variant in create_variability(batchdata):
                    config = pipeline_form.data

                    # Modify all the necessary bits
                    for mod in variant:
                        config = update_data(config, mod)

                    _trigger_preview(config)

    def _delete_history_item(_):
        i = center.selected_index
        nonlocal history
        history = history[:i] + history[i + 1 :]
        center.children = center.children[:i] + center.children[i + 1 :]
        center.selected_index = len(center.children) - 1

        # This ensures that widgets are updated when this tab is removed
        _switch_tab(None)

    def _delete_all(_):
        nonlocal history
        history = []
        center.children = tuple()

    # Register preview button click handler
    preview.on_click(_update_preview)

    # Register delete button click handler
    delete.on_click(_delete_history_item)
    delete_all.on_click(_delete_all)

    # When we switch tabs, all widgets should restore the correct information
    center.observe(_switch_tab, names="selected_index")

    # Create the (persisting) building blocks for the app
    pipeline_form = pipeline.widget_form()

    # Get a widget for rasterization
    raster_schema = copy.deepcopy(load_schema("rasterize.json"))

    # We drop classification, because we add this as a specialized widget
    raster_schema["properties"].pop("classification")

    rasterization_widget_form = ipywidgets_jsonschema.Form(
        raster_schema, vertically_place_labels=True
    )
    rasterization_widget = rasterization_widget_form.widget
    rasterization_widget.layout = fullwidth

    # Get a widget that allows configuration of the visualization method
    schema = load_schema("visualization.json")
    visualization_form = ipywidgets_jsonschema.Form(
        schema, vertically_place_labels=True
    )
    visualization_form_widget = visualization_form.widget
    visualization_form_widget.layout = fullwidth

    # Get the container widget for classification
    class_widget = ipywidgets.Box([])
    class_widget.layout = fullwidth

    # Create the final app layout
    app = ipywidgets.AppLayout(
        left_sidebar=ipywidgets.VBox(
            [
                ipywidgets.HTML(
                    "Interactive pipeline configuration:", layout=fullwidth
                ),
                pipeline_form.widget,
            ]
        ),
        center=center,
        right_sidebar=ipywidgets.VBox(
            [
                ipywidgets.HTML("Ground point filtering controls:", layout=fullwidth),
                preview,
                finalize,
                ipywidgets.HBox([delete, delete_all]),
                ipywidgets.HTML("Rasterization options:", layout=fullwidth),
                rasterization_widget,
                ipywidgets.HTML("Visualization options:", layout=fullwidth),
                visualization_form_widget,
                ipywidgets.HTML(
                    "Point classifications to include in the hillshade visualization (click preview to update):",
                    layout=fullwidth,
                ),
                class_widget,
            ]
        ),
    )

    # Initially trigger preview generation
    preview.click()

    # Show the app in Jupyter notebook
    IPython.display.display(app)

    # Implement finalization
    pipeline_proxy = return_proxy(
        lambda: pipeline.copy(
            _variability=pipeline_form.batchdata, **pipeline_form.data
        ),
        pipeline_form,
    )

    def _finalize(_):
        app.layout.display = "none"

    finalize.on_click(_finalize)

    # Return the pipeline proxy object
    return pipeline_proxy


def setup_rasterize_side_panel(dataset):
    # Get a widget for rasterization
    raster_schema = copy.deepcopy(load_schema("rasterize.json"))

    # We drop classification, because we add this as a specialized widget
    raster_schema["properties"].pop("classification")

    rasterization_widget_form = ipywidgets_jsonschema.Form(
        raster_schema, vertically_place_labels=True
    )
    rasterization_widget = rasterization_widget_form.widget
    rasterization_widget.layout = fullwidth

    # Get a widget that allows configuration of the visualization method
    schema = load_schema("visualization.json")

    form = ipywidgets_jsonschema.Form(schema, vertically_place_labels=True)
    formwidget = form.widget
    formwidget.layout = fullwidth

    # Create the classification widget
    classification = ipywidgets.Box([classification_widget([dataset])])
    classification.layout = fullwidth

    widged_list = [rasterization_widget, formwidget, classification]
    form_list = [rasterization_widget_form, form]

    return widged_list, form_list


def assign_pipeline(segmentation, pipelines, finalization_hook=lambda x: x):
    """
    Load a Segmentation object with one or more multipolygons and a list of pipelines.
    Each multipolygon can be assigned to one pipeline.

    """

    print()


def create_segmentation(
    dataset, show_right_side=False, finalization_hook=lambda x: x, pipelines=None
):
    """The Jupyter UI to create a segmentation object from scratch.

    The use of this UI will soon be described in detail.
    """
    # create instance of dataset with srs of "EPSG:3857",
    # this ensures that the slope and hillshade overlay fit the map projection.
    dataset = reproject_dataset(dataset, "EPSG:3857")
    # Create the necessary widgets

    map_ = Map(dataset=dataset)
    map_widget = map_.show()
    finalize = ipywidgets.Button(description="Finalize")

    widged_list, form_list = setup_rasterize_side_panel(dataset)
    rasterization_widget, formwidget, classification = widged_list
    rasterization_widget_form, form = form_list

    map_widget.layout = fullwidth
    finalize.layout = fullwidth
    # Get a visualization button and add it to the control panel
    load_raster_button = ipywidgets.Button(
        description="Load rasterization", layout=fullwidth
    )

    load_raster_label = ipywidgets.Box(
        (ipywidgets.Label("Add Geotiff layer to the map:"),)
    )

    # The return proxy object
    segmentation_proxy = return_proxy(
        lambda: Segmentation(map_.return_segmentation()), map_.draw_control
    )

    if show_right_side == True:
        print("show right side")
        # right side controls
        # these are used to assign a segmentation to each

        # passes the segment to the _update_seg_pin function
        def on_button_clicked(b, coordinates_mean=None):
            return _update_seg_pin(coordinates_mean)

        # holds a segmentation and calculates
        def _update_seg_pin(coordinates_mean):
            # initilizes a new marker
            marker = Marker(
                location=[coordinates_mean[1], coordinates_mean[0]], draggable=False
            )
            # removes the previous marker from the map
            for layer in map_.map.layers:
                if type(layer) == Marker:

                    map_.map.remove_layer(layer)
            # adds the new marker to the selected polygon
            map_.map.add_layer(marker)

            # this doesnt show

        def _update_seg_list(draw_control_change_event):

            if len(draw_control_change_event.new) > len(draw_control_change_event.old):
                features = segmentation_proxy["features"]
                # calculate the geometry center of the new segmentation.
                # this is passed through the button to update the pin
                coordinates = np.squeeze((features[-1]["geometry"]["coordinates"]))
                coordinates_mean = list(np.mean(coordinates, axis=0))

                label = ipywidgets.Label(
                    f"Segmentation {len( features )}",
                    layout=ipywidgets.Layout(width="80%"),
                )
                button = ipywidgets.Button(
                    icon="fa-location-dot", layout=ipywidgets.Layout(width="20%")
                )
                button.on_click(
                    functools.partial(
                        on_button_clicked, coordinates_mean=coordinates_mean
                    )
                )

                # pipelines need to know where they are stored/found
                # author is a placeholder
                new_dropdown = ipywidgets.Dropdown(
                    options=[
                        (pipeline.title, pipeline.location) for pipeline in pipelines
                    ],
                    layout=fullwidth,
                )

                box = ipywidgets.VBox(
                    children=[ipywidgets.HBox(children=[label, button]), new_dropdown]
                )

                right_side.children = right_side.children + (box,)
            else:
                print("one instance was removed")
                for i, (new_feature, old_feature) in enumerate(
                    zip(draw_control_change_event.new, draw_control_change_event.old)
                ):
                    print("new", new_feature)
                    print("old", old_feature)
                    if new_feature != old_feature:
                        print(i)
                    print()

        map_.draw_control.observe(_update_seg_list, names="data")
        ride_side_label = ipywidgets.Box(
            (ipywidgets.Label("Assign Pipelines to Segmentations"),)
        )

        right_side = ipywidgets.VBox(
            [
                ride_side_label,
            ]
        )

        # Arrange controls into one widget

        controls = ipywidgets.VBox(
            [
                load_raster_label,
                load_raster_button,
                rasterization_widget,
                formwidget,
                classification,
            ]
        )
        # Create the overall app layout

        app = ipywidgets.AppLayout(
            header=ipywidgets.HBox(
                [finalize], layout=ipywidgets.Layout(height="1", width="auto")
            ),
            left_sidebar=controls,
            center=map_widget,
            right_sidebar=right_side,
            footer=None,
            pane_widths=[1, 3, 1],
        )

    else:
        print("only left")
        # Arrange them into one widget

        controls = ipywidgets.VBox(
            [
                finalize,
                load_raster_label,
                load_raster_button,
                rasterization_widget,
                formwidget,
                classification,
            ]
        )
        # Create the overall app layout

        app = ipywidgets.AppLayout(
            header=None,
            left_sidebar=controls,
            center=map_widget,
            right_sidebar=None,
            footer=None,
            pane_widths=[1, 3, 0],
        )

    # used to prevent recalculation of geotiff layers
    parameter_cache = []

    def load_raster_to_map(b):
        with hourglass_icon(b):
            # Rerasterize if necessary
            nonlocal dataset
            if not isinstance(dataset, DigitalSurfaceModel):
                dataset = dataset.rasterize(
                    classification=classification.children[0].value,
                    **rasterization_widget_form.data,
                )

            else:
                dataset = dataset.dataset.rasterize(
                    classification=classification.children[0].value,
                    **rasterization_widget_form.data,
                )

            # put all options into a dict and filter out the numer of points
            options = [
                (option[1], option[0].split(":")[1].split(" (")[0])
                for option in classification.children[0].options
            ]
            classification_dict = {}
            for key, value in options:
                classification_dict[key] = value
            # take only the currently active classifications for layer description.
            classification_str = ", ".join(
                [classification_dict[i] for i in classification.children[0].value]
            )

            title = f"""{form.data.visualization_type}:
                        res: {rasterization_widget_form.data.resolution}"""
            # this string is used to prevent recalculation of geotiffs
            new_parameter_str = f"""{form.data.visualization_type}:
                        res: {rasterization_widget_form.data.resolution}
                       {", ".join([str(key) + ": " + str(value) for key, value in form.data.items()])},
                         classification: ({classification_str}))"""

            # only calculate a new layer if the configuration has not been added yet.
            if new_parameter_str not in parameter_cache:
                vis = dataset.show(**form.data).children[0]
                map_.load_overlay(vis, title)
                parameter_cache.append(new_parameter_str)

    # Show the final widget
    load_raster_button.on_click(load_raster_to_map)

    IPython.display.display(app)

    if show_right_side == True:

        def _finalize_segmentations(_):
            app.layout.display = "none"
            if len(right_side.children) > 1:
                for segmentation, dropdown in zip(
                    segmentation_proxy["features"], right_side.children[1:]
                ):
                    segmentation["pipeline"] = dropdown.value

            segmentation_proxy.__wrapped__ = finalization_hook(
                segmentation_proxy.__wrapped__
            )

        finalize.on_click(_finalize_segmentations)

    else:

        def _finalize_simple(_):
            app.layout.display = "none"
            segmentation_proxy.__wrapped__ = finalization_hook(
                segmentation_proxy.__wrapped__
            )

        finalize.on_click(_finalize_simple)

    return segmentation_proxy


def create_upload(filetype, finalization_hook=lambda x: x):
    """Create a Jupyter UI snippet that allows a user to upload a file

    :param filetype:
        The file extension to expect for the upload.
    :type filetype: str
    """

    confirm_button = ipywidgets.Button(
        description="Confirm upload",
        disabled=False,
        button_style="",  # 'success', 'info', 'warning', 'danger' or ''
        tooltip="Confirm upload",
        icon="check",  # (FontAwesome names without the `fa-` prefix)
    )
    upload = ipywidgets.FileUpload(
        accept=filetype,  # Accepted file extension e.g. '.txt', '.pdf', 'image/*', 'image/*,.pdf'
        multiple=True,  # True to accept multiple files upload else False
    )

    layout = ipywidgets.Layout(width="100%")
    confirm_button.layout = layout
    upload.layout = layout
    app = ipywidgets.VBox([upload, confirm_button])
    IPython.display.display(app)
    upload_proxy = return_proxy(lambda: upload, upload)

    def _finalize(_):
        app.layout.display = "none"
        upload_proxy.__wrapped__ = finalization_hook(upload_proxy.__wrapped__)

    confirm_button.on_click(_finalize)
    return upload_proxy


def show_interactive(dataset, filtering_callback=None, update_classification=False):
    """The interactive UI to visualize a dataset

    :param dataset:
        The Lidar dataset to visualize
    :type dataset: adaptivefiltering.DataSet
    :param filtering_callback:
        A callback that is called to transform the dataset before visualization.
        This may be used to hook in additional functionality like the execution
        of a filtering pipeline
    :type pipeline: Callable
    :param update_classification:
        Whether or not the classification values shown in the UI need to be updated
        for each preview. Boils down to the question of whether :code:`filtering_callback`
        potentially changes the classification of the dataset.
    :type update_classification: bool
    """

    # If dataset is not rasterized already, do it now
    if not isinstance(dataset, DigitalSurfaceModel):
        dataset = dataset.rasterize()

    widged_list, form_list = setup_rasterize_side_panel(dataset)
    rasterization_widget, formwidget, classification = widged_list
    rasterization_widget_form, form = form_list

    # Get a visualization button and add it to the control panel
    button = ipywidgets.Button(description="Visualize", layout=fullwidth)
    controls = ipywidgets.VBox(
        [button, rasterization_widget, formwidget, classification]
    )

    # Get a container widget for the visualization itself
    content = ipywidgets.Box([ipywidgets.Label("Currently rendering visualization...")])

    # Create the overall app layout
    app = ipywidgets.AppLayout(
        header=None,
        left_sidebar=controls,
        center=content,
        right_sidebar=None,
        footer=None,
        pane_widths=[1, 3, 0],
    )

    def trigger_visualization(b):
        with hourglass_icon(b):
            # Maybe call the given callback
            nonlocal dataset
            if filtering_callback is not None:
                dataset = filtering_callback(dataset.dataset).rasterize()

            # Maybe update the classification widget if necessary
            if update_classification:
                nonlocal classification
                classification.children = (classification_widget([dataset]),)

            # Rerasterize if necessary
            dataset = dataset.dataset.rasterize(
                classification=classification.children[0].value,
                **rasterization_widget_form.data,
            )

            # Trigger visualization
            app.center.children = (dataset.show(**form.data),)

    # Get a visualization button
    button.on_click(trigger_visualization)

    # Click the button once to trigger initial visualization
    button.click()

    return app


def select_pipeline_from_library(multiple=False):
    """The Jupyter UI to select filtering pipelines from libraries.

    The use of this UI is described in detail in `the notebook on filtering libraries`_.

    .. _the notebook on filtering libraries: libraries.nblink

    :param multiple:
        Whether or not it should be possible to select multiple filter pipelines.
    :type multiple: bool
    :return:
        Returns the selected pipeline object(s)
    :rtype: adaptivefiltering.filter.Pipeline
    """

    def library_name(lib):
        if lib.name is not None:
            return lib.name
        else:
            return lib.path

    # Collect checkboxes in the selection menu
    library_checkboxes = [
        ipywidgets.Checkbox(value=True, description=library_name(lib), indent=False)
        for lib in get_filter_libraries()
    ]
    backend_checkboxes = {
        name: ipywidgets.Checkbox(value=cls.enabled(), description=name, indent=False)
        for name, cls in Filter._filter_impls.items()
        if Filter._filter_is_backend[name]
    }

    # Extract all authors that contributed to the filter libraries
    def get_author(f):
        if f.author == "":
            return "(unknown)"
        else:
            return f.author

    all_authors = []
    for lib in get_filter_libraries():
        for f in lib.filters:
            all_authors.append(get_author(f))
    all_authors = list(sorted(set(all_authors)))

    # Create checkbox widgets for the all authors
    author_checkboxes = {
        author: ipywidgets.Checkbox(value=True, description=author, indent=False)
        for author in all_authors
    }

    # Use a TagsInput widget for keywords
    keyword_widget = ipywidgets.TagsInput(
        value=library_keywords(),
        allow_duplicates=False,
        tooltip="Keywords to filter for. Filters need to match at least one given keyword in order to be shown.",
    )

    # Create the filter list widget
    filter_list = []
    widget_type = ipywidgets.SelectMultiple if multiple else ipywidgets.Select
    filter_list_widget = widget_type(
        options=[f.title for f in filter_list],
        value=[] if multiple else None,
        description="",
        layout=fullwidth,
    )

    # Create the pipeline description widget
    metadata_schema = load_schema("pipeline.json")["properties"]["metadata"]
    metadata_form = WidgetFormWithLabels(metadata_schema, vertically_place_labels=True)

    def metadata_updater(change):
        # The details of how to access this from the change object differs
        # for Select and SelectMultiple
        if multiple:
            # Check if the change selected a new entry
            if len(change["new"]) > len(change["old"]):
                # If so, we display the metadata of the newly selected one
                (entry,) = set(change["new"]) - set(change["old"])
                metadata_form.data = filter_list[entry].config["metadata"]
        else:
            metadata_form.data = filter_list[change["new"]].config["metadata"]

    filter_list_widget.observe(metadata_updater, names="index")

    # Define a function that allows use to access the selected filters
    def accessor():
        indices = filter_list_widget.index
        if indices is None:
            return None

        # Either return a tuple of filters or a single filter
        if multiple:
            return tuple(filter_list[i] for i in indices)
        else:
            return filter_list[indices]

    # A function that recreates the filtered list of filters
    def update_filter_list(_):
        filter_list.clear()

        # Iterate over all libraries to find filters
        for i, lbox in enumerate(library_checkboxes):
            # If the library is deactivated -> skip
            if not lbox.value:
                continue

            # Iterate over all filters in the given library
            for filter_ in get_filter_libraries()[i].filters:
                # If the filter uses a deselected backend -> skip
                if any(
                    not bbox.value and name in filter_.used_backends()
                    for name, bbox in backend_checkboxes.items()
                ):
                    continue

                # If the author of this pipeline has been deselected -> skip
                if not author_checkboxes[get_author(filter_)].value:
                    continue

                # If the filter does not have at least one selected keyword -> skip
                # Exception: No keywords are specified at all in the library (early dev)
                if library_keywords():
                    if not set(keyword_widget.value).intersection(
                        set(filter_.keywords)
                    ):
                        continue

                # Once we got here we use the filter
                filter_list.append(filter_)

        # Update the widget
        nonlocal filter_list_widget
        filter_list_widget.value = [] if multiple else None
        filter_list_widget.options = [f.title for f in filter_list]

    # Trigger it once in the beginning
    update_filter_list(None)

    # Make all checkbox changes trigger the filter list update
    for box in itertools.chain(
        library_checkboxes, backend_checkboxes.values(), author_checkboxes.values()
    ):
        box.observe(update_filter_list, names="value")

    # Piece all of the above selcetionwidgets together into an accordion
    acc = ipywidgets.Accordion(
        children=[
            ipywidgets.VBox(children=tuple(library_checkboxes)),
            ipywidgets.VBox(children=tuple(backend_checkboxes.values())),
            keyword_widget,
            ipywidgets.VBox(children=tuple(author_checkboxes.values())),
        ],
        titles=["Libraries", "Backends", "Keywords", "Author"],
    )

    button = ipywidgets.Button(description="Finalize", layout=fullwidth)

    # Piece things together into an app layout
    app = ipywidgets.AppLayout(
        left_sidebar=acc,
        center=filter_list_widget,
        right_sidebar=ipywidgets.VBox([button, metadata_form.widget]),
        pane_widths=(1, 1, 1),
    )
    IPython.display.display(app)

    # Return proxy handling
    proxy = return_proxy(accessor, filter_list_widget)

    def _finalize(_):
        # If nothing has been selected, the finalize button is no-op
        if accessor():
            app.layout.display = "none"

    button.on_click(_finalize)

    return proxy


def select_pipelines_from_library():
    """The Jupyter UI to select filtering pipelines from libraries.

    The use of this UI is described in detail in `the notebook on filtering libraries`_.

    .. _the notebook on filtering libraries: libraries.nblink

    :return:
        Returns the selected pipeline object(s)
    :rtype: adaptivefiltering.filter.Pipeline
    """

    return select_pipeline_from_library(multiple=True)


def select_best_pipeline(dataset=None, pipelines=None):
    """Select the best pipeline for a given dataset.

    The use of this UI is described in detail in `the notebook on selecting filter pipelines`_.

    .. _the notebook on selecting filter pipelines: selection.nblink

    :param dataset:
        The dataset to use for visualization of ground point filtering results
    :type dataset: adaptivefiltering.DataSet
    :param pipelines:
        The tentative list of pipelines to try. May e.g. have been selected using
        the select_pipelines_from_library tool.
    :type pipelines: list
    :return:
        The selected pipeline with end user configuration baked in
    :rtype: adaptivefiltering.filter.Pipeline
    """
    if dataset is None:
        raise AdaptiveFilteringError("A dataset is required for 'select_best_pipeline'")

    if pipelines is None:
        raise AdaptiveFilteringError(
            "At least one pipeline needs to be passed to 'select_best_pipeline'"
        )

    # Finalize button
    finalize = ipywidgets.Button(
        description="Finalize (including end-user configuration into filter)",
        layout=ipywidgets.Layout(width="100%"),
    )

    # Per-pipeline data structures to keep track off
    subwidgets = []
    pipeline_accessors = []

    # Subwidget generator function
    def interactive_pipeline(p):
        # A widget that contains the variability
        varform = ipywidgets_jsonschema.Form(
            p.variability_schema, vertically_place_labels=True, use_sliders=False
        )

        # Piggy-back onto the visualization app
        vis = show_interactive(
            dataset,
            filtering_callback=lambda ds: cached_pipeline_application(
                ds, p, **varform.data
            ),
            update_classification=True,
        )

        # Insert the variability form
        vis.right_sidebar = ipywidgets.VBox(
            children=[ipywidgets.Label("Customization points:"), varform.widget]
        )
        vis.pane_widths = [1, 2, 1]

        # Insert the generated widgets into the outer structures
        subwidgets.append(vis)

        pipeline_accessors.append(
            lambda: p.copy(**p._modify_filter_config(varform.data))
        )

    # Trigger subwidget generation for all pipelines
    for p in pipelines:
        interactive_pipeline(p)

    # Tabs that contain the interactive execution with all given pipelines
    if len(subwidgets) > 1:
        tabs = ipywidgets.Tab(
            children=subwidgets, titles=[f"#{i}" for i in range(len(pipelines))]
        )
    elif len(subwidgets) == 1:
        tabs = subwidgets[0]
    else:
        tabs = ipywidgets.Box()

    app = ipywidgets.VBox([finalize, tabs])
    IPython.display.display(app)

    def _return_handler():
        # Get the current selection index of the Tabs widget (if any)
        if len(subwidgets) > 1:
            index = tabs.selected_index
        elif len(subwidgets) == 1:
            index = 0
        else:
            return Pipeline()

        return pipeline_accessors[index]()

    # Return proxy handling
    proxy = return_proxy(_return_handler, tabs)

    def _finalize(_):
        app.layout.display = "none"

    finalize.on_click(_finalize)

    return proxy


def execute_interactive(dataset, pipeline):
    """Interactively apply a filter pipeline to a given dataset in Jupyter

    This allows you to interactively explore the effects of end user configuration
    values specified by the filtering pipeline.

    :param dataset:
        The dataset to work on
    :type dataset: adaptivefiltering.DataSet
    :param pipeline:
        The pipeline to execute.
    :type pipelines: adaptivefiltering.filter.Pipeline
    :return:
        The pipeline with the end user configuration baked in
    :rtype: adaptivefiltering.filter.Pipeline
    """

    return select_best_pipeline(dataset=dataset, pipelines=[pipeline])
