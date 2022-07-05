from afwizard.lastools import *

import pyrsistent
import pytest


@pytest.mark.skipif(not lastools_is_present(), reason="LASTools not found.")
def test_lastools(minimal_dataset):
    # Instantiate a default filter object
    f = LASToolsFilter()

    # Make sure that the filter widget can be displayed
    widget = f.widget_form()

    # And that the filter can be reconstructed using the form data
    f2 = f.copy(**pyrsistent.thaw(widget.data))

    # Apply the filter
    dataset = f.execute(minimal_dataset)
