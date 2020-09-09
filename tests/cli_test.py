"""Test cli.

honeybee-core currently doesn't have many commands but nevertheless it is good to have a
sample code for reference. For more information see Click's documentation:

http://click.palletsprojects.com/en/7.x/testing/

"""
import sys

from click.testing import CliRunner
from honeybee.cli import viz
from honeybee.cli.validate import validate_model, validate_model_basic, \
    validate_model_geometry


def test_viz():
    runner = CliRunner()
    result = runner.invoke(viz)
    assert result.exit_code == 0
    assert result.output.startswith('vi')
    assert result.output.endswith('z!\n')


def test_validate_model():
    input_model = './tests/json/single_family_home.hbjson'
    incorrect_input_model = './tests/json/bad_geometry_model.hbjson'
    if (sys.version_info >= (3, 7)):
        runner = CliRunner()
        result = runner.invoke(validate_model, [input_model])
        assert result.exit_code == 0
        runner = CliRunner()
        result = runner.invoke(validate_model, [incorrect_input_model])
        assert result.exit_code == 1


def test_validate_model_basic():
    input_model = './tests/json/single_family_home.hbjson'
    if (sys.version_info >= (3, 7)):
        runner = CliRunner()
        result = runner.invoke(validate_model_basic, [input_model])
        assert result.exit_code == 0


def test_validate_model_geometry():
    input_model = './tests/json/single_family_home.hbjson'
    if (sys.version_info >= (3, 7)):
        runner = CliRunner()
        result = runner.invoke(validate_model_geometry, [input_model])
        assert result.exit_code == 0
