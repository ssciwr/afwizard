import logging

# Configure the basic logger
logger = logging.getLogger("adaptivefiltering")
logger.setLevel(logging.WARNING)
_handler = logging.StreamHandler()
logger.addHandler(_handler)
_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
_handler.setFormatter(_formatter)
