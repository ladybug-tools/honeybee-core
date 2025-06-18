"""honeybee validation commands."""
import sys
import logging
import click

from ladybug.commandutil import process_content_to_output
from honeybee.model import Model

_logger = logging.getLogger(__name__)


@click.group(help='Commands for validating Honeybee objects.')
def validate():
    pass


@validate.command('model')
@click.argument('model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--extension', '-e', help='Text for the name of the extension to be checked. '
    'The value input is case-insensitive such that "radiance" and "Radiance" will '
    'both result in the model being checked for validity with honeybee-radiance. '
    'This value can also be set to "Generic" in order to run checks for all installed '
    'extensions. Using "Generic" will run all except the most limiting of checks '
    '(eg. the DOE2 lack of support for courtyards) with the goal of producing a model '
    'that can be exported to multiple engines (albeit with a little extra '
    'postprocessing for particularly limited engines). Some common honeybee extension '
    'names that can be input here include: Radiance, EnergyPlus, DOE2, IES, IDAICE',
    type=str, default='Generic', show_default=True)
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
    '--room-overlaps', 'room_overlaps', flag_value='True',
    help='Deprecated flag used to check room collisions. '
    'Use `honeybee validate room-collisions` instead.')
@click.option(
    '--output-file', '-f', help='Optional file to output the full report '
    'of the validation. By default it will be printed out to stdout',
    type=click.File('w'), default='-')
def validate_model_cli(model_file, extension, plain_text, room_overlaps, output_file):
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
        if room_overlaps == 'True':
            print('--room-overlaps option is deprecated. '
                  'Use `honeybee validate room-collisions` instead.')
            validate_room_collisions(model_file, json, output_file)
        else:
            validate_model(model_file, extension, json, output_file)
    except Exception as e:
        _logger.exception('Model validation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def validate_model(model_file, extension='Generic', json=False, output_file=None,
                   plain_text=True):
    """Validate all properties of a Model file against the Honeybee schema.

    This includes checking basic compliance with the 5 rules of honeybee geometry
    as well as checks for all extension attributes.

    Args:
        model_file: Full path to a Honeybee Model file.
        extension_name: Text for the name of the extension to be checked.
            The value input here is case-insensitive such that "radiance"
            and "Radiance" will both result in the model being checked for
            validity with honeybee-radiance. This value can also be set to
            "Generic" in order to run checks for all installed extensions.
            Using "Generic" will run all except the most limiting of checks
            (eg. DOE2's lack of support for courtyards) with the goal of
            producing a model that is export-able to multiple engines (albeit
            with a little extra postprocessing for particularly limited engines).
            Some common dragonfly extension names that can be input here if they
            are installed include:

            * Radiance
            * EnergyPlus
            * DOE2
            * IES
            * IDAICE

        json: Boolean to note whether the output validation report should be
            formatted as a JSON object instead of plain text. (Default: False).
        output_file: Optional file to output the full report of the validation.
            If None, the string will simply be returned from this method.
    """
    report = Model.validate(model_file, 'check_for_extension', [extension], json)
    return process_content_to_output(report, output_file)


@validate.command('rooms-solid')
@click.argument('model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--plain-text/--json', ' /-j', help='Flag to note whether the output validation '
    'report should be formatted as a JSON object instead of plain text. If set to JSON, '
    'the output object will contain several attributes. An attribute called '
    '"fatal_error" is a text string containing an exception if the Model failed to '
    'serialize and will be an empty string if serialization was successful. An '
    'attribute called "errors" will contain a list of JSON objects for each '
    'invalid issue. A boolean attribute called "valid" will note whether the Model '
    'is valid or not.',
    default=True, show_default=True)
@click.option(
    '--output-file', '-f', help='Optional file to output the full report '
    'of the validation. By default it will be printed out to stdout.',
    type=click.File('w'), default='-')
def validate_rooms_solid_cli(model_file, plain_text, output_file):
    """Validate whether all Room volumes in a model are solid.

    The returned result can include a list of all naked and non-manifold edges
    preventing closed room volumes when --json is used. This is helpful for visually
    identifying issues in geometry that are preventing the room volume from
    validating as closed.

    \b
    Args:
        model_file: Full path to a Honeybee Model file.
    """
    try:
        json = not plain_text
        validate_rooms_solid(model_file, json, output_file)
    except Exception as e:
        _logger.exception('Model room volume validation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def validate_rooms_solid(model_file, json=False, output_file=None, plain_text=True):
    """Get a list of all naked and non-manifold edges preventing closed room volumes.

    This is helpful for visually identifying issues in geometry that are preventing
    the room volume from reading as closed.

    Args:
        model_file: Full path to a Honeybee Model file.
        json: Boolean to note whether the output validation report should be
            formatted as a JSON object instead of plain text. (Default: False).
        output_file: Optional file to output the full report of the validation.
            If None, the string will simply be returned from this method.
    """
    report = Model.validate(model_file, 'check_rooms_solid', json_output=json)
    return process_content_to_output(report, output_file)


@validate.command('room-collisions')
@click.argument('model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--plain-text/--json', ' /-j', help='Flag to note whether the output validation '
    'report should be formatted as a JSON object instead of plain text. If set to JSON, '
    'the output object will contain several attributes. An attribute called '
    '"fatal_error" is a text string containing an exception if the Model failed to '
    'serialize and will be an empty string if serialization was successful. An '
    'attribute called "errors" will contain a list of JSON objects for each '
    'invalid issue. A boolean attribute called "valid" will note whether the Model '
    'is valid or not.', default=True, show_default=True)
@click.option(
    '--output-file', '-f', help='Optional file to output the full report '
    'of the validation. By default it will be printed out to stdout.',
    type=click.File('w'), default='-')
def validate_room_collisions_cli(model_file, plain_text, output_file):
    """Validate whether Room collide with one another beyond the model tolerance.

    \b
    Args:
        model_file: Full path to a Honeybee Model file.
    """
    try:
        json = not plain_text
        validate_room_collisions(model_file, json, output_file)
    except Exception as e:
        _logger.exception('Model room volume validation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def validate_room_collisions(model_file, json=False, output_file=None, plain_text=True):
    """Validate whether Room collide with one another beyond the model tolerance.

    Args:
        model_file: Full path to a Honeybee Model file.
        json: Boolean to note whether the output validation report should be
            formatted as a JSON object instead of plain text. (Default: False).
        output_file: Optional file to output the full report of the validation.
            If None, the string will simply be returned from this method.
    """
    report = Model.validate(model_file, 'check_room_volume_collisions', json_output=json)
    return process_content_to_output(report, output_file)
