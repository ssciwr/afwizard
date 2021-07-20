from adaptivefiltering.opals import _automated_opals_schema, opals_is_present

from click.testing import CliRunner
import json
import pytest


@pytest.mark.skipif(not opals_is_present(), reason="OPALS not found.")
@pytest.mark.parametrize("mod", ["Grid", "Cell", "RobFilter"])
def test_hello_world(mod):
    runner = CliRunner()
    result = runner.invoke(_automated_opals_schema, [mod])
    assert result.exit_code == 0
    json.loads(result.stdout)
