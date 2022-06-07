from afwizard.opals import *
from afwizard.pdal import PDALInMemoryDataSet
from afwizard.utils import AFwizardError

import jsonschema
import os
import pyrsistent
import pytest


# The list of implemented modules
_availableOpalsModules = [
    "RobFilter",
]


@pytest.mark.skipif(not opals_is_present(), reason="OPALS not found.")
def test_set_opals_directory(monkeypatch):
    dir = os.environ["OPALS_DIR"]

    # Remove the OPALS directory from the environment
    monkeypatch.delenv("OPALS_DIR")

    # Set it using the API
    set_opals_directory(dir)
    assert opals_is_present()
    set_opals_directory(None)

    # Check that we correctly validate an OPALS path
    with pytest.raises(AFwizardError):
        set_opals_directory("bla")
    assert not opals_is_present()


@pytest.mark.skipif(not opals_is_present(), reason="OPALS not found.")
def test_get_opals_module_executable():
    # Looking for a non-existent OPALS module should throw
    with pytest.raises(AFwizardError):
        get_opals_module_executable("NonExist")

    # Looking for implemented ones should always succeed
    for mod in _availableOpalsModules:
        assert os.path.exists(get_opals_module_executable(mod))


def test_get_opals_module_executable_failure(monkeypatch):
    # In the absence of OPALS, asking for a module should throw
    monkeypatch.delenv("OPALS_DIR", raising=False)
    for mod in _availableOpalsModules:
        with pytest.raises(AFwizardError):
            get_opals_module_executable(mod)


@pytest.mark.skipif(not opals_is_present(), reason="OPALS not found.")
def test_opals():
    # A filter that does not set a type should raise an error
    with pytest.raises(jsonschema.ValidationError):
        OPALSFilter()

    # Instantiate a filter
    f = OPALSFilter(type="RobFilter")

    # Make sure that the filter widget can be displayed
    widget = f.widget_form()

    # And that the filter can be reconstructed using the form data
    f2 = f.copy(**pyrsistent.thaw(widget.data))


@pytest.mark.skipif(not opals_is_present(), reason="OPALS not found.")
@pytest.mark.parametrize("mod", _availableOpalsModules)
def test_minimal_default_filter_settings(mod, minimal_dataset):
    # TODO: The following is a temporary workaround until we properly
    #       normalize the configuration values according to the schema's
    #       default definition. My first attempt did not get through the
    #       schema's anyOf field and added erroneous fields.
    try:
        f = OPALSFilter(type=mod)
    except jsonschema.ValidationError:
        f = OPALSFilter(type=mod, feature=["mean"])

    dataset = f.execute(minimal_dataset)


@pytest.mark.skipif(not opals_is_present(), reason="OPALS not found.")
@pytest.mark.slow
@pytest.mark.parametrize("mod", _availableOpalsModules)
def test_default_filter_settings(mod, dataset):
    # TODO: The following is a temporary workaround until we properly
    #       normalize the configuration values according to the schema's
    #       default definition. My first attempt did not get through the
    #       schema's anyOf field and added erroneous fields.
    try:
        f = OPALSFilter(type=mod)
    except jsonschema.ValidationError:
        f = OPALSFilter(type=mod, feature=["mean"])

    dataset = f.execute(dataset)


@pytest.mark.skipif(not opals_is_present(), reason="OPALS not found.")
def test_opals_datamanager(minimal_dataset):
    # Convert to ODM
    odm = OPALSDataManagerObject.convert(minimal_dataset)
    old_file = odm.filename
    assert odm.filename is not None

    # Check idempotency
    odm2 = OPALSDataManagerObject.convert(odm)
    assert old_file == odm2.filename

    # Check conversion into PDAL object and back
    pdal = PDALInMemoryDataSet.convert(odm)
    assert pdal.data.shape[0] > 0
    back = OPALSDataManagerObject.convert(pdal)
