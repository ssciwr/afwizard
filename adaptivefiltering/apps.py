from adaptivefiltering.asprs import asprs_class_name
from adaptivefiltering.dataset import DataSet
from adaptivefiltering.filter import Pipeline
from adaptivefiltering.pdal import PDALInMemoryDataSet
from adaptivefiltering.segmentation import InteractiveMap, Segmentation

import ipywidgets
import IPython
import itertools
import math
import numpy as np
import os


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


def classification_widget(datasets):
    """Create a widget to select classification values"""

    def get_classes(dataset):
        # Make sure that we have an in-memory copy of the dataset
        dataset = PDALInMemoryDataSet.convert(dataset)

        # Get the lists present in this dataset
        return np.unique(dataset.data["Classification"])

    # Join the classes in all datasets
    classes = set().union(*tuple(set(get_classes(d)) for d in datasets))

    return ipywidgets.SelectMultiple(
        options=[
            (f"{asprs_class_name(code)} ({code})", code) for code in sorted(classes)
        ],
        value=list(sorted(classes)),
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
    class_widget = classification_widget(datasets)

    # Configure control buttons
    preview = ipywidgets.Button(description="Preview")
    finalize = ipywidgets.Button(description="Finalize")

    def _update_preview(_):
        # Update the pipeline object according to the widget
        nonlocal pipeline
        pipeline = pipeline.copy(**form.data)

        # Update all widgets one after another
        # TODO: Do this in parallel!
        for d, w in zip(datasets, widgets):
            transformed = pipeline.execute(d)
            newfig = transformed.show_hillshade(classification=class_widget.value)
            w.figure.axes[0].images[0].set_data(newfig.axes[0].images[0].get_array())
            w.draw()
            w.flush_events()

    preview.on_click(_update_preview)

    # Define the most commonly used layout classes
    layout = ipywidgets.Layout(width="100%")

    # Create the filter configuration widget including layout tweaks
    left_sidebar = ipywidgets.VBox(
        [
            ipywidgets.HTML("Interactive pipeline configuration:", layout=layout),
            form.widget,
        ]
    )

    # Create the center widget including layout tweaks
    if len(widgets) > 1:
        center = ipywidgets.Tab()
        center.children = widgets
        center.titles = tuple(f"Dataset #{i}" for i in range(len(widgets)))
        print(center.titles)
    else:
        center = widgets[0]
    center.layout = layout

    # Create the right sidebar including layout tweaks
    preview.layout = layout
    finalize.layout = layout
    class_widget.layout = layout
    right_sidebar = ipywidgets.VBox(
        [
            ipywidgets.HTML("Ground point filtering controls:", layout=layout),
            preview,
            finalize,
            ipywidgets.HTML(
                "Point classifications to include in the hillshade visualization (click preview to update):",
                layout=layout,
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

    def get_value():
        return upload

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
