from afwizard.opals import _automated_opals_schema, opals_is_present
from afwizard.paths import copy_notebooks

from .test_opals import _availableOpalsModules

from click.testing import CliRunner
import glob
import json
import os
import pytest


@pytest.mark.skipif(not opals_is_present(), reason="OPALS not found.")
@pytest.mark.parametrize("mod", _availableOpalsModules)
def test_opals_schema_cli(mod):
    runner = CliRunner()
    result = runner.invoke(_automated_opals_schema, mod)
    assert result.exit_code == 0
    schema = json.loads(result.stdout)
    assert len(schema) > 0


def test_copy_notebooks(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(copy_notebooks, os.getcwd())
    assert result.exit_code == 0
    assert len(glob.glob("*.ipynb")) > 0
