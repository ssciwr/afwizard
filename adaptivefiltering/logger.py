import logging

# Configure the basic logger
logger = logging.getLogger("adaptivefiltering")
logger.setLevel(logging.WARNING)
_handler = logging.StreamHandler()
logger.addHandler(_handler)
_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
_handler.setFormatter(_formatter)


def attach_file_logger(filename):
    handler = logging.FileHandler(filename)
    handler.setFormatter(_handler)
    logger.addHandler(handler)
