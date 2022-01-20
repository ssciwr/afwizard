from adaptivefiltering.asprs import asprs_class_name
from adaptivefiltering.dataset import DataSet, DigitalSurfaceModel
from adaptivefiltering.filter import Pipeline, Filter
from adaptivefiltering.library import get_filter_libraries
from adaptivefiltering.paths import load_schema, within_temporary_workspace
from adaptivefiltering.pdal import PDALInMemoryDataSet
from adaptivefiltering.segmentation import Map, Segmentation
from adaptivefiltering.widgets import WidgetForm

import contextlib
import copy
import ipywidgets
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


def pipeline_tuning(datasets=[], pipeline=None):
    # Instantiate a new pipeline object if we are not modifying an existing one.
    if pipeline is None:
        pipeline = Pipeline()

    # If a single dataset was given, transform it into a list
    if isinstance(datasets, DataSet):
        datasets = [datasets]

    # Get the widget form for this pipeline
    form = pipeline.widget_form()

    # Get a widget for rasterization
    raster_schema = copy.deepcopy(load_schema("rasterize.json"))

    # We drop classification, because we add this as a specialized widget
    raster_schema["properties"].pop("classification")

    rasterization_widget_form = WidgetForm(raster_schema)
    rasterization_widget = rasterization_widget_form.widget
    rasterization_widget.layout = fullwidth

    # Get a widget that allows configuration of the visualization method
    schema = load_schema("visualization.json")
    visualization_form = WidgetForm(schema)
    visualization_form_widget = visualization_form.widget
    visualization_form_widget.layout = fullwidth

    # Get the classification value selection widget
    _class_widget = classification_widget(datasets)
    class_widget = ipywidgets.Box([_class_widget])

    # Configure control buttons
    preview = ipywidgets.Button(description="Preview")
    finalize = ipywidgets.Button(description="Finalize")

    # Create widgets from the datasets
    widgets = [
        ds.show(
            classification=class_widget.children[0].value,
            **rasterization_widget_form.data,
        )
        for ds in datasets
    ]

    # If no datasets were given, we add a dummy widget that explains the situation
    if not widgets:
        widgets = [
            sized_label(
                "Please call with datasets for interactive visualization", size=18
            )
        ]

    def _update_preview(button):
        with hourglass_icon(button):
            # Update the pipeline object according to the widget
            nonlocal pipeline
            pipeline = pipeline.copy(**form.data)

            # Apply the pipeline to all datasets
            # TODO: Do this in parallel!
            with within_temporary_workspace():
                transformed_datasets = [
                    cached_pipeline_application(d, pipeline) for d in datasets
                ]

            # Update the classification widget with the classes now present in datasets
            selected = class_widget.children[0].value
            class_widget.children = (
                classification_widget(transformed_datasets, selected=selected),
            )

            # Write new widgets
            new_widgets = [
                ds.show(
                    classification=class_widget.children[0].value,
                    **rasterization_widget_form.data,
                    **visualization_form.data,
                )
                for ds in transformed_datasets
            ]

            nonlocal app
            app.center = create_center_widget(new_widgets)

    preview.on_click(_update_preview)

    # Create the filter configuration widget including layout tweaks
    left_sidebar = ipywidgets.VBox(
        [
            ipywidgets.HTML("Interactive pipeline configuration:", layout=fullwidth),
            form.widget,
        ]
    )

    def create_center_widget(widgets):
        # Create the center widget including layout tweaks
        if len(widgets) > 1:
            # We use the Tab widget to allow switching between different datasets
            center = ipywidgets.Tab(children=widgets)

            # Set titles for the different tabs
            for i in range(len(widgets)):
                center.set_title(i, f"Dataset #{i}")

            center.layout = fullwidth

            return center
        else:
            widgets[0].layout = ipywidgets.Layout(
                width="100%", flex_flow="column", align_items="center", display="flex"
            )
            return widgets[0]

    # Create the right sidebar including layout tweaks
    preview.layout = fullwidth
    finalize.layout = fullwidth
    class_widget.layout = fullwidth
    right_sidebar = ipywidgets.VBox(
        [
            ipywidgets.HTML("Ground point filtering controls:", layout=fullwidth),
            preview,
            finalize,
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
    )

    # Create the final app layout
    app = ipywidgets.AppLayout(
        header=None,
        left_sidebar=left_sidebar,
        center=create_center_widget(widgets),
        right_sidebar=right_sidebar,
        footer=None,
        pane_widths=[3, 6, 3],
    )

    # Show the app in Jupyter notebook
    IPython.display.display(app)

    # Implement finalization
    pipeline_proxy = InteractiveWidgetOutputProxy(lambda: pipeline.copy(**form.data))

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
        lambda: Segmentation(map_.return_polygon())
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

    rasterization_widget_form = WidgetForm(raster_schema)
    rasterization_widget = rasterization_widget_form.widget
    rasterization_widget.layout = fullwidth

    # Get a widget that allows configuration of the visualization method
    schema = load_schema("visualization.json")
    form = WidgetForm(schema)
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
    )

    # Name the accordion options
    acc.set_title(0, "Libraries")
    acc.set_title(1, "Backends")

    # Introduce a two column layout
    return ipywidgets.HBox(children=(acc, filter_list_widget)), accessor
