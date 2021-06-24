"""Test basic CLI commands and the validate group"""
import sys
import json

from click.testing import CliRunner
from honeybee.cli import viz, config
from honeybee.cli.validate import validate_model


def test_viz():
    runner = CliRunner()
    result = runner.invoke(viz)
    assert result.exit_code == 0
    assert result.output.startswith('vi')
    assert result.output.endswith('z!\n')


def test_config():
    runner = CliRunner()
    result = runner.invoke(config)
    assert result.exit_code == 0
    config_dict = json.loads(result.output)
    assert len(config_dict) >= 5


def test_validate_model():
    input_model = './tests/json/single_family_home.hbjson'
    incorrect_input_model = './tests/json/bad_geometry_model.hbjson'
    if (sys.version_info >= (3, 7)):
        runner = CliRunner()
        result = runner.invoke(validate_model, [input_model])
        print(result.output)
        assert result.exit_code == 0
        runner = CliRunner()
        result = runner.invoke(validate_model, [incorrect_input_model])
        outp = result.output
        assert 'Your Model is invalid for the following reasons' in outp
        assert 'is not coplanar or fully bounded by its parent Face' in outp
