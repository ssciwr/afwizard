from adaptivefiltering.asprs import asprs_class_name
from adaptivefiltering.dataset import DataSet
from adaptivefiltering.filter import Pipeline
from adaptivefiltering.paths import load_schema
from adaptivefiltering.pdal import PDALInMemoryDataSet
from adaptivefiltering.segmentation import InteractiveMap, Segmentation
from adaptivefiltering.widgets import WidgetForm

import ipywidgets
import IPython
import itertools
import math
import numpy as np


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


def classification_widget(datasets, selected=None):
    """Create a widget to select classification values"""

    def get_classes(dataset):
        # Make sure that we have an in-memory copy of the dataset
        dataset = PDALInMemoryDataSet.convert(dataset)

        # Get the lists present in this dataset
        return np.unique(dataset.data["Classification"])

    # Join the classes in all datasets
    classes = set().union(*tuple(set(get_classes(d)) for d in datasets))

    # Determine selection - either all or the ones that were passed and exist
    if selected is None:
        selected = list(sorted(classes))
    else:
        selected = [s for s in selected if s in classes]

    return ipywidgets.SelectMultiple(
        options=[
            (f"{asprs_class_name(code)} ({code})", code) for code in sorted(classes)
        ],
        value=selected,
    )


def pipeline_tuning(datasets=[], pipeline=None):
    # Instantiate a new pipeline object if we are not modifying an existing one.
    if pipeline is None:
        pipeline = Pipeline()

    # If a single dataset was given, transform it into a list
    if isinstance(datasets, DataSet):
        datasets = [datasets]

    # Create widgets from the datasets
    widgets = [ds.show_hillshade().canvas for ds in datasets]

    # If no datasets were given, we add a dummy widget that explains the situation
    if not widgets:
        widgets = [
            sized_label(
                "Please call with datasets for interactive visualization", size=18
            )
        ]

    # Get the widget form for this pipeline
    form = pipeline.widget_form()

    # Get the classification value selection widget
    _class_widget = classification_widget(datasets)
    class_widget = ipywidgets.Box([_class_widget])

    # Configure control buttons
    preview = ipywidgets.Button(description="Preview")
    finalize = ipywidgets.Button(description="Finalize")

    def _update_preview(_):
        # Update the pipeline object according to the widget
        nonlocal pipeline
        pipeline = pipeline.copy(**form.data)

        # Apply the pipeline to all datasets
        # TODO: Do this in parallel!
        transformed_datasets = [pipeline.execute(d) for d in datasets]

        # Update the classification widget with the classes now present in datasets
        selected = class_widget.children[0].value
        class_widget.children = (
            classification_widget(transformed_datasets, selected=selected),
        )

        # Update the widgets
        for d, w in zip(transformed_datasets, widgets):
            newfig = d.show_hillshade(classification=class_widget.children[0].value)
            w.figure.axes[0].images[0].set_data(newfig.axes[0].images[0].get_array())
            w.draw()
            w.flush_events()

    preview.on_click(_update_preview)

    # Create the filter configuration widget including layout tweaks
    left_sidebar = ipywidgets.VBox(
        [
            ipywidgets.HTML("Interactive pipeline configuration:", layout=fullwidth),
            form.widget,
        ]
    )

    # Create the center widget including layout tweaks
    if len(widgets) > 1:
        # We use the Tab widget to allow switching between different datasets
        center = ipywidgets.Tab()

        # The wrapping in Box works around a known bug in ipympl:
        # https://github.com/matplotlib/ipympl/issues/126
        center.children = tuple(ipywidgets.Box([w]) for w in widgets)

        # Set titles for the different tabs
        for i in range(len(widgets)):
            center.set_title(i, f"Dataset #{i}")
    else:
        center = widgets[0]
    center.layout = fullwidth

    # Create the right sidebar including layout tweaks
    preview.layout = fullwidth
    finalize.layout = fullwidth
    class_widget.layout = fullwidth
    right_sidebar = ipywidgets.VBox(
        [
            ipywidgets.HTML("Ground point filtering controls:", layout=fullwidth),
            preview,
            finalize,
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
        center=center,
        right_sidebar=right_sidebar,
        footer=None,
        pane_widths=[2, 3, 1],
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
    map_ = InteractiveMap(dataset=dataset)
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
    # Convert to PDAL - this should go away when we make DEM's a first class citizen
    # of our abstractions. We do this here instead of the visualization functions to
    # reuse the converted dataset across the interactive session
    dataset = PDALInMemoryDataSet.convert(dataset)

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
    controls = ipywidgets.VBox([button, formwidget, classification])

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

    def trigger_visualization(_):
        # This is necessary to work around matplotlib weirdness
        app.center.children[0].layout.display = "none"
        app.center.children = (
            dataset.show(classification=classification.value, **form.data),
        )

    # Get a visualization button
    button.on_click(trigger_visualization)

    # Click the button once to trigger initial visualization
    button.click()

    return app
