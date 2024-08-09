"""honeybee validation commands."""
import sys
import logging
import json as py_json
import click

from honeybee.model import Model
from honeybee.config import folders

_logger = logging.getLogger(__name__)


@click.group(help='Commands for validating Honeybee objects.')
def validate():
    pass


@validate.command('model')
@click.argument('model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--check-all/--room-overlaps', ' /-ro', help='Flag to note whether the output '
    'validation report should validate all possible issues with the model or only '
    'the Room collisions should be checked.', default=True, show_default=True)
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
def validate_model_cli(model_file, check_all, plain_text, output_file):
    """Validate all properties of a Model file against Honeybee schema.

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
        model_file: Full path to a Model JSON file.
    """
    try:
        json = not plain_text
        room_overlaps = not check_all
        validate_model(model_file, room_overlaps, json, output_file)
    except Exception as e:
        _logger.exception('Model validation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def validate_model(model_file, room_overlaps=False, json=False, output_file=None,
                   check_all=True, plain_text=True):
    """Validate all properties of a Model file against the Honeybee schema.

    This includes checking basic compliance with the 5 rules of honeybee geometry
    as well as checks for all extension attributes.

    Args:
        model_file: Full path to a Honeybee Model file.
        room_overlaps: Boolean to note whether the output validation report
            should only validate the Room collisions (True) or all possible
            issues with the model should be checked (False). (Default: False).
        json: Boolean to note whether the output validation report should be
            formatted as a JSON object instead of plain text.
        output_file: Optional file to output the string of the visualization
            file contents. If None, the string will simply be returned from
            this method.
        """
    if not json:
        # re-serialize the Model to make sure no errors are found
        c_ver = folders.honeybee_core_version_str
        s_ver = folders.honeybee_schema_version_str
        ver_msg = 'Validating Model using honeybee-core=={} and ' \
            'honeybee-schema=={}'.format(c_ver, s_ver)
        print(ver_msg)
        parsed_model = Model.from_file(model_file)
        print('Re-serialization passed.')
        # perform several other checks for geometry rules and others
        if not room_overlaps:
            report = parsed_model.check_all(raise_exception=False, detailed=False)
        else:
            report = parsed_model.check_room_volume_collisions(raise_exception=False)
        print('Model checks completed.')
        # check the report and write the summary of errors
        if report == '':
            full_msg = ver_msg + '\nCongratulations! Your Model is valid!'
        else:
            full_msg = ver_msg + \
                '\nYour Model is invalid for the following reasons:\n' + report
        if output_file is None:
            return full_msg
        else:
            output_file.write(full_msg)
    else:
        out_dict = {
            'type': 'ValidationReport',
            'app_name': 'Honeybee',
            'app_version': folders.honeybee_core_version_str,
            'schema_version': folders.honeybee_schema_version_str
        }
        try:
            parsed_model = Model.from_file(model_file)
            out_dict['fatal_error'] = ''
            if not room_overlaps:
                errors = parsed_model.check_all(raise_exception=False, detailed=True)
            else:
                errors = parsed_model.check_room_volume_collisions(
                    raise_exception=False, detailed=True)
            out_dict['errors'] = errors
            out_dict['valid'] = True if len(out_dict['errors']) == 0 else False
        except Exception as e:
            out_dict['fatal_error'] = str(e)
            out_dict['errors'] = []
            out_dict['valid'] = False
        if output_file is None:
            return py_json.dumps(out_dict, indent=4)
        else:
            output_file.write(py_json.dumps(out_dict, indent=4))


@validate.command('room-volumes')
@click.argument('model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--output-file', '-f', help='Optional file to output the JSON strings of '
    'ladybug_geometry LineSegment3Ds that represent naked and non-manifold edges. '
    'By default it will be printed out to stdout', type=click.File('w'), default='-')
def validate_room_volumes_cli(model_file, output_file):
    """Get a list of all naked and non-manifold edges preventing closed room volumes.

    This is helpful for visually identifying issues in geometry that are preventing
    the room volume from reading as closed.

    \b
    Args:
        model_file: Full path to a Honeybee Model file.
    """
    try:
        validate_room_volumes(model_file, output_file)
    except Exception as e:
        _logger.exception('Model room volume validation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def validate_room_volumes(model_file, output_file=None):
    """Get a list of all naked and non-manifold edges preventing closed room volumes.

    This is helpful for visually identifying issues in geometry that are preventing
    the room volume from reading as closed.

    Args:
        model_file: Full path to a Honeybee Model file.
        output_file: Optional file to output the string of the visualization
            file contents. If None, the string will simply be returned from
            this method.
    """
    # re-serialize the Model and collect all naked and non-manifold edges
    parsed_model = Model.from_file(model_file)
    problem_edges = []
    for room in parsed_model.rooms:
        if not room.geometry.is_solid:
            problem_edges.extend(room.geometry.naked_edges)
            problem_edges.extend(room.geometry.non_manifold_edges)
    # write the new model out to the file or stdout
    prob_array = [lin.to_dict() for lin in problem_edges]
    if output_file is None:
        return py_json.dumps(prob_array)
    else:
        output_file.write(py_json.dumps(prob_array))
