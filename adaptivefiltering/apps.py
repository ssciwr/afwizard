from adaptivefiltering.dataset import DataSet
from adaptivefiltering.filter import Pipeline

import ipython_blocking
import ipywidgets
import IPython
import itertools
import math


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


def block_until_button_click(button):
    """Block the execution of the Jupyter notebook until a button was clicked

    This can be used for "Save", "Continue" or "Done" buttons that finalize
    the frontend input given into Jupyter widgets. The technique used to achieve
    this is taken from :code:`ipython_blocking`.

    :param button:
        The button widget to wait for. The function does not create or display
        the widget, but merely registers the necessary handler.
    :type button: ipywidgets.Button
    """
    keep_running = True

    def _handler(_):
        nonlocal keep_running
        keep_running = False

    button.on_click(_handler)

    ctx = ipython_blocking.CaptureExecution(replay=True)
    with ctx:
        while keep_running:
            ctx.step()


def flex_square_layout(widgets):
    # Arrange the widgets in a flexible square layout
    grid_cols = math.ceil(math.sqrt(len(widgets)))
    grid_rows = math.ceil(len(widgets) / grid_cols)

    # Fill the given widgets into a GridspecLayout
    grid = ipywidgets.GridspecLayout(grid_rows, grid_cols)
    for i, xy in enumerate(itertools.product(range(grid_rows), range(grid_cols))):
        if i < len(widgets):
            grid[xy] = widgets[i]

    return grid


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

    # Configure the finalize button
    finalize = ipywidgets.Button(description="Finalize")

    # Create the app layout
    app = ipywidgets.AppLayout(
        header=None,
        left_sidebar=form.widget,
        right_sidebar=flex_square_layout(widgets),
        footer=finalize,
        pane_widths=[1, 0, 2],
    )

    # Show the app in Jupyter notebook
    IPython.display.display(app)

    # Wait until the finalize button was clicked
    block_until_button_click(finalize)

    # Construct the new pipeline object
    pipeline = pipeline.copy(**form.data)

    # Hide the widget to prevent reuse of the same widget
    app.layout.display = "none"

    # Return the pipeline object
    return pipeline
