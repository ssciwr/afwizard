from afwizard.opals import _automated_opals_schema, opals_is_present

from .test_opals import _availableOpalsModules

from click.testing import CliRunner
import json
import pytest


@pytest.mark.skipif(not opals_is_present(), reason="OPALS not found.")
@pytest.mark.parametrize("mod", _availableOpalsModules)
def test_opals_schema_cli(mod):
    runner = CliRunner()
    result = runner.invoke(_automated_opals_schema, mod)
    assert result.exit_code == 0
    schema = json.loads(result.stdout)
    assert len(schema) > 0
