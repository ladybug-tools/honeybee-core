"""Test the comparison CLI commands"""
import json

from click.testing import CliRunner
from honeybee.cli.compare import compare_models


def test_compare_model():
    base_model = './tests/json/minor_geometry/existing_model.hbjson'
    other_model = './tests/json/minor_geometry/updated_model.hbjson'
    runner = CliRunner()
    result = runner.invoke(compare_models, [base_model, other_model])
    assert result.exit_code == 0
    outp = result.output
    assert 'CHANGED OBJECTS' in outp
    assert 'ADDED OBJECTS' in outp
    assert 'DELETED OBJECTS' in outp

    runner = CliRunner()
    result = runner.invoke(compare_models, [base_model, other_model, '--json'])
    compare_dict = json.loads(result.output)
    assert len(compare_dict['changed_objects']) == 9
    assert len(compare_dict['added_objects']) == 1
    assert len(compare_dict['deleted_objects']) == 1
