"""Test cli.

honeybee-core currently doesn't have many commands but nevertheless it is good to have a
sample code for reference. For more information see Click's documentation:

http://click.palletsprojects.com/en/7.x/testing/

"""
from click.testing import CliRunner
from honeybee.cli import viz

def test_viz():
    runner = CliRunner()
    result = runner.invoke(viz)
    assert result.exit_code == 0
    assert result.output.startswith('vi')
    assert result.output.endswith('z!\n')
