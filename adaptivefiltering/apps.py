from adaptivefiltering.filter import Pipeline

import ipython_blocking
import ipywidgets
import IPython


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


def pipeline_tuning(datasets=[], pipeline=None):
    # Instantiate a new pipeline object if we are not modifying an existing one.
    if pipeline is None:
        pipeline = Pipeline()

    # Get the widget form for this pipeline
    form = pipeline.widget_form()

    # Configure the finalize button
    finalize = ipywidgets.Button(description="Finalize")

    # Create the app layout
    app = ipywidgets.AppLayout(
        header=sized_label("Interactively tuning filter pipeline:", size=24),
        center=form.widget,
        right_sidebar=ipywidgets.Text("Rechts"),
        footer=finalize,
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
