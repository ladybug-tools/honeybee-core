"""honeybee validation commands."""
import sys
import logging
import json
import click

from honeybee.model import Model
from honeybee.config import folders

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
        click.echo(
            'Validating Model using honeybee-core=={} and honeybee-schema=={}'.format(
                folders.honeybee_core_version_str, folders.honeybee_schema_version_str
            ))
        parsed_model = Model.from_hbjson(model_json)
        click.echo('Re-serialization passed.')
        # perform several other checks for geometry rules and others
        report = parsed_model.check_all(raise_exception=False)
        click.echo('Model checks completed.')
        # check the report and write the summary of errors
        if report == '':
            output_file.write('Congratulations! Your Model is valid!')
        else:
            error_msg = '\nYour Model is invalid for the following reasons:'
            output_file.write('\n'.join([error_msg, report]))
    except Exception as e:
        _logger.exception('Model validation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@validate.command('room-volumes')
@click.argument('model-json', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--output-file', '-f', help='Optional file to output the JSON strings of '
    'ladybug_geometry LineSegment3Ds that represent naked and non-manifold edges. '
    'By default it will be printed out to stdout', type=click.File('w'), default='-')
def validate_room_volumes(model_json, output_file):
    """Get a list of all naked and non-manifold edges preventing closed room volumes.

    This is helpful for visually identifying issues in geometry that are preventing
    the room volume from reading as closed.

    \b
    Args:
        model_json: Full path to a Model JSON file.
    """
    try:
        # re-serialize the Model and collect all naked and non-maifold edges
        parsed_model = Model.from_hbjson(model_json)
        problem_edges = []
        for room in parsed_model.rooms:
            if not room.geometry.is_solid:
                problem_edges.extend(room.geometry.naked_edges)
                problem_edges.extend(room.geometry.non_manifold_edges)
        # write the new model out to the file or stdout
        prob_array = [lin.to_dict() for lin in problem_edges]
        output_file.write(json.dumps(prob_array))
    except Exception as e:
        _logger.exception('Model room volume validation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)
