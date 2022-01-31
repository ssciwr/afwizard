from adaptivefiltering.asprs import asprs_class_name
from adaptivefiltering.dataset import DataSet, DigitalSurfaceModel
from adaptivefiltering.filter import Pipeline, Filter, update_data
from adaptivefiltering.library import get_filter_libraries, library_keywords
from adaptivefiltering.paths import load_schema, within_temporary_workspace
from adaptivefiltering.pdal import PDALInMemoryDataSet
from adaptivefiltering.segmentation import Map, Segmentation
from adaptivefiltering.utils import AdaptiveFilteringError

import collections
import contextlib
import copy
import ipywidgets
import ipywidgets_jsonschema
import IPython
import itertools
import math
import numpy as np
import pytools


def sized_label(text, size=12):
    """Create a text label widget with a given font size

    :param text:
        The text to show.
    :type text: str
    :param size:
        The fontsize
    :type size: int
    """
    return ipywidgets.HTML(value=f"<h3 style='font-size: {str(size)}px'>{text}</h>")


fullwidth = ipywidgets.Layout(width="100%")


class InteractiveWidgetOutputProxy:
    def __init__(self, creator, finalization_hook=lambda obj: obj):
        """An object to capture interactive widget output

        :param creator:
            A callable accepting no parameters that constructs the return
            object. It will typically depend on widget state.
        :type creator: Callable
        """
        # Save the creator function for later use
        self._creator = creator
        self._finalization_hook = finalization_hook

        # Try instantiating the object
        try:
            self._obj = creator()
        except:
            self._obj = None

        # Store whether this object has been finalized
        self._finalized = False

        # Docstring Forwarding
        self.__doc__ = getattr(self._obj, "__doc__", "")

    def _finalize(self):
        """Finalize the return object.

        After this function is called once, no further updates of the return
        object are carried out.
        """
        self._obj = self._creator()
        self._obj = self._finalization_hook(self._obj)
        self._finalized = True

    def __getattr__(self, attr):
        # If not finalized, we recreate the object on every member access
        if not self._finalized:
            self._obj = self._creator()

        # Forward this to the actual object
        return getattr(self._obj, attr)


@contextlib.contextmanager
def hourglass_icon(button):
    """Context manager to show an hourglass icon while processing"""
    button.icon = "hourglass-half"
    yield
    button.icon = ""


def flex_square_layout(widgets):
    """Place widgets into a grid layout that is approximately square."""
    # Arrange the widgets in a flexible square layout
    grid_cols = math.ceil(math.sqrt(len(widgets)))
    grid_rows = math.ceil(len(widgets) / grid_cols)

    # Fill the given widgets into a GridspecLayout
    grid = ipywidgets.GridspecLayout(grid_rows, grid_cols)
    for i, xy in enumerate(itertools.product(range(grid_rows), range(grid_cols))):
        if i < len(widgets):
            grid[xy] = widgets[i]

    return grid


def as_pdal(dataset):
    if isinstance(dataset, DigitalSurfaceModel):
        return as_pdal(dataset.dataset)
    return PDALInMemoryDataSet.convert(dataset)


def classification_widget(datasets, selected=None):
    """Create a widget to select classification values"""

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
    if 2 in joined_count:
        selected = [2]
    elif selected is None:
        # If there are no ground points, we use all classes
        selected = list(joined_count.keys())

    return ipywidgets.SelectMultiple(
        options=[
            (f"[{code}]: {asprs_class_name(code)} ({joined_count[code]} points)", code)
            for code in sorted(joined_count.keys())
        ],
        value=selected,
    )


@pytools.memoize(key=lambda d, p: (d, p.config))
def cached_pipeline_application(dataset, pipeline):
    return pipeline.execute(dataset)


def expand_variability_string(varlist, type_="string", samples_for_continuous=5):
    """Split a string into variants allowing comma separation and ranges with dashes"""
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
    """Create combinatorical product of specified variants"""
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
    def create_history_item(ds, data):
        # Create a new classification widget and insert it into the Box
        _class_widget = classification_widget([ds])
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

        for ds in datasets:
            # Extract the pipeline from the widget
            nonlocal pipeline
            pipeline = pipeline.copy(**config)

            # TODO: Do this in parallel!
            with within_temporary_workspace():
                transformed = cached_pipeline_application(ds, pipeline)

            # Create a new entry in the history list
            create_history_item(transformed, config)

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

    # Initially seed with a simple visualization
    for ds in datasets:
        create_history_item(ds, pipeline_form.data)

    # Show the app in Jupyter notebook
    IPython.display.display(app)

    # Implement finalization
    pipeline_proxy = InteractiveWidgetOutputProxy(
        lambda: pipeline.copy(
            _variability=pipeline_form.batchdata, **pipeline_form.data
        )
    )

    def _finalize(_):
        app.layout.display = "none"
        pipeline_proxy._finalize()

    finalize.on_click(_finalize)

    # Return the pipeline proxy object
    return pipeline_proxy


def create_segmentation(dataset):
    # Create the necessary widgets
    map_ = Map(dataset=dataset)
    map_widget = map_.show()
    finalize = ipywidgets.Button(description="Finalize")

    # Arrange them into one widget
    layout = ipywidgets.Layout(width="100%")
    map_widget.layout = layout
    finalize.layout = layout
    app = ipywidgets.VBox([map_widget, finalize])

    # Show the final widget
    IPython.display.display(app)

    # The return proxy object
    segmentation_proxy = InteractiveWidgetOutputProxy(
        lambda: Segmentation(map_.return_segmentation())
    )

    def _finalize(_):
        app.layout.display = "none"
        segmentation_proxy._finalize()

    finalize.on_click(_finalize)

    return segmentation_proxy


def create_upload(filetype):

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
    upload_proxy = InteractiveWidgetOutputProxy(lambda: upload)

    def _finalize(_):
        app.layout.display = "none"
        upload_proxy._finalize()

    confirm_button.on_click(_finalize)
    return upload_proxy


def show_interactive(dataset):
    # If dataset is not rasterized already, do it now
    if not isinstance(dataset, DigitalSurfaceModel):
        dataset = dataset.rasterize()

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
    classification = classification_widget([dataset])
    classification.layout = fullwidth

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
            # Rerasterize if necessary
            nonlocal dataset
            dataset = dataset.dataset.rasterize(
                classification=classification.value, **rasterization_widget_form.data
            )

            # Trigger visualization
            app.center.children = (dataset.show(**form.data),)

    # Get a visualization button
    button.on_click(trigger_visualization)

    # Click the button once to trigger initial visualization
    button.click()

    return app


def filter_selection_widget(multiple=False):
    def library_name(lib):
        if lib.name is not None:
            return lib.name
        else:
            return lib.path

    # Collect checkboxes in the selection menu
    library_checkboxes = [
        ipywidgets.Checkbox(value=True, description=library_name(lib))
        for lib in get_filter_libraries()
    ]
    backend_checkboxes = {
        name: ipywidgets.Checkbox(value=cls.enabled(), description=name)
        for name, cls in Filter._filter_impls.items()
        if Filter._filter_is_backend[name]
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
    filter_list_widget = ipywidgets.Box(
        children=(
            widget_type(
                options=[f.title for f in filter_list],
                value=[] if multiple else None,
                description="",
            ),
        )
    )

    # Define a function that allows use to access the selected filters
    def accessor():
        indices = filter_list_widget.children[0].index
        if indices is None:
            return ()
        if not multiple:
            indices = (indices,)
        return tuple(filter_list[i] for i in indices)

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

                # If the filter does not have at least one selected keyword -> skip
                if not set(keyword_widget.value).intersection(set(filter_.keywords)):
                    continue

                # Once we got here we use the filter
                filter_list.append(filter_)

        # Update the widget
        nonlocal filter_list_widget
        filter_list_widget.children = (
            widget_type(
                options=[f.title for f in filter_list],
                value=[] if multiple else None,
                description="",
            ),
        )

    # Trigger it once in the beginning
    update_filter_list(None)

    # Make all checkbox changes trigger the filter list update
    for box in itertools.chain(library_checkboxes, backend_checkboxes.values()):
        box.observe(update_filter_list, names="value")

    # Piece all of the above selcetionwidgets together into an accordion
    acc = ipywidgets.Accordion(
        children=[
            ipywidgets.VBox(children=tuple(library_checkboxes)),
            ipywidgets.VBox(children=tuple(backend_checkboxes.values())),
        ],
        titles=["Libraries", "Backends"],
    )

    # Introduce a two column layout
    return ipywidgets.HBox(children=(acc, filter_list_widget)), accessor


def choose_pipeline():
    widget, accessor = filter_selection_widget()
    button = ipywidgets.Button(description="Finalize", layout=fullwidth)

    # Piece things together
    app = ipywidgets.VBox(children=[widget, button])
    IPython.display.display(app)

    # Return proxy handling
    proxy = InteractiveWidgetOutputProxy(lambda: accessor()[0])

    def _finalize(_):
        if len(accessor()) != 0:
            app.layout.display = "none"
            proxy._finalize()

    button.on_click(_finalize)

    return proxy
