"""honeybee validation commands."""
import sys
import logging
import json
import click

from honeybee.model import Model
from honeybee.config import folders

_logger = logging.getLogger(__name__)


@click.group(help='Commands for validating Honeybee objects.')
def validate():
    pass


@validate.command('model')
@click.argument('model-json', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--plain-text/--json', ' /-j', help='Flag to note whether the output validation '
    'report should be formatted as a JSON object instead of plain text. If set to JSON, '
    'the output object will contain several attributes. The "honeybee_core" and '
    '"honeybee_schema" attributes will note the versions of these libraries used in '
    'the validation process. An attribute called "fatal_error" is a text string '
    'containing an exception if the Model failed to serialize and will be an empty '
    'string if serialization was successful. An attribute called "errors" will '
    'contain a list of JSON objects for each invalid issue found in the model. A '
    'boolean attribute called "valid" will note whether the Model is valid or not.',
    default=True, show_default=True)
@click.option(
    '--output-file', '-f', help='Optional file to output the full report '
    'of the validation. By default it will be printed out to stdout',
    type=click.File('w'), default='-')
def validate_model(model_json, plain_text, output_file):
    """Validate all properties of a Model file against the Honeybee schema.

    This includes checking basic compliance with the 5 rules of honeybee geometry
    as well as checks for all extension attributes. The 5 rules of honeybee geometry
    are as follows.

    1. All Face3Ds must be planar to within the model tolerance.

    2. All Face3Ds must NOT be self-intersecting (like a bowtie shape)

    3. All children sub-faces (Apertures and Doors) must be co-planar with
        their parent Face and lie completely within its boundary.

    4. All adjacent object pairs (faces and sub-faces with a Surface boundary
        condition) must have matching areas.

    5. All Room volumes must be closed solids.

    \b
    Args:
        model_json: Full path to a Model JSON file.
    """
    try:
        if plain_text:
            # re-serialize the Model to make sure no errors are found
            click.echo(
                'Validating Model using honeybee-core=={} and honeybee-schema=={}'.format(
                    folders.honeybee_core_version_str, folders.honeybee_schema_version_str
                ))
            parsed_model = Model.from_hbjson(model_json)
            click.echo('Re-serialization passed.')
            # perform several other checks for geometry rules and others
            report = parsed_model.check_all(raise_exception=False, detailed=False)
            click.echo('Model checks completed.')
            # check the report and write the summary of errors
            if report == '':
                output_file.write('Congratulations! Your Model is valid!')
            else:
                error_msg = '\nYour Model is invalid for the following reasons:'
                output_file.write('\n'.join([error_msg, report]))
        else:
            out_dict = {
                'type': 'ValidationReport',
                'honeybee_core': folders.honeybee_core_version_str,
                'honeybee_schema': folders.honeybee_schema_version_str
            }
            try:
                parsed_model = Model.from_hbjson(model_json)
                out_dict['fatal_error'] = ''
                out_dict['errors'] = \
                    parsed_model.check_all(raise_exception=False, detailed=True)
                out_dict['valid'] = True if len(out_dict['errors']) == 0 else False
            except Exception as e:
                out_dict['fatal_error'] = str(e)
                out_dict['errors'] = []
                out_dict['valid'] = False
            output_file.write(json.dumps(out_dict, indent=4))
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
        # re-serialize the Model and collect all naked and non-manifold edges
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
