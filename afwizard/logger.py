import ipywidgets
import logging

# Configure the basic logger
logger = logging.getLogger("afwizard")
logger.setLevel(logging.DEBUG)
_handler = logging.StreamHandler()
_handler.setLevel(logging.WARNING)
logger.addHandler(_handler)
_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
_handler.setFormatter(_formatter)


def attach_file_logger(filename):
    handler = logging.FileHandler(filename, mode="w")
    handler.setFormatter(_handler)
    logger.addHandler(handler)


class OutputWidgetHandler(logging.Handler):
    def __init__(self, widget):
        self.widget = widget
        super().__init__()
        self.setFormatter(_formatter)
        self.setLevel(logging.INFO)

    def emit(self, record):
        record = self.format(record)
        self.widget.outputs = (
            {"name": "stdout", "output_type": "stream", "text": record},
        ) + self.widget.outputs


class LoggingOutputWidget(ipywidgets.Output):
    def __init__(self, *args, **kwargs):
        # Initialize the output widget
        super().__init__(*args, **kwargs)

        # Create a connected handler
        self.handler = OutputWidgetHandler(self)
        logger.addHandler(self.handler)


def create_foldable_log_widget():
    return ipywidgets.Accordion(
        children=(LoggingOutputWidget(),),
        titles=("Log output",),
        layout=ipywidgets.Layout(height="200px"),
    )
