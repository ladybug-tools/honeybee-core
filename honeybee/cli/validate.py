"""honeybee validation commands."""
import click
import sys
import logging

from honeybee.model import Model

_logger = logging.getLogger(__name__)


@click.group(help='Commands for validating Honeybee JSON files.')
def validate():
    pass


@validate.command('model')
@click.argument('model-json', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--output-file', '-f', help='Optional file to output the full report '
    'of any errors detected. By default it will be printed out to stdout',
    type=click.File('w'), default='-')
def validate_model(model_json, output_file):
    """Validate all properties of a Model JSON file against the Honeybee schema.

    This includes basic properties like adjacency checks and all geometry checks.

    \b
    Args:
        model_json: Full path to a Model JSON file.
    """
    try:
        # re-serialize the Model to make sure no errors are found in re-serialization
        click.echo('Validating Model JSON ...')
        parsed_model = Model.from_hbjson(model_json)
        click.echo('Python re-serialization passed.')
        # perform several other checks for geometry rules and others
        report = parsed_model.check_all(raise_exception=False)
        click.echo('Model geometry and identifier checks completed.')
        # check the report and write the summary of errors
        if report == '':
            output_file.write('Congratulations! Your Model JSON is valid!')
        else:
            error_msg = '\nYour Model is invalid for the following reasons:'
            output_file.write('\n'.join([error_msg, report]))
    except Exception as e:
        _logger.exception('Model validation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)
