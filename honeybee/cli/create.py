"""honeybee model creation commands."""
import click
import sys
import logging
import json

from honeybee.model import Model
from honeybee.boundarycondition import boundary_conditions as bcs
try:
    ad_bc = bcs.adiabatic
except AttributeError:  # honeybee_energy is not loaded and adiabatic does not exist
    ad_bc = None

_logger = logging.getLogger(__name__)


@click.group(help='Commands for creating Honeybee models.')
def create():
    pass


@create.command('shoe-box')
@click.argument('width', type=float)
@click.argument('depth', type=float)
@click.argument('height', type=float)
@click.option('--orientation-angle', '-a', help='A number between 0 and 360 for the '
              'clockwise orientation of the box in degrees. (0=North, 90=East, 180='
              'South, 270=West).', type=float, default=0, show_default=True)
@click.option('--window-ratio', '-wr', help='A number between 0 and 1 (but not equal '
              'to 1) for the ratio between aperture area and area of the face pointing '
              'towards the orientation-angle. Using 0 will generate no windows',
              type=float, default=0, show_default=True)
@click.option('--adiabatic/--outdoors', ' /-o', help='Flag to note whether the faces '
              'that are not in the direction of the orientation-angle are adiabatic or '
              'outdoors.', default=True, show_default=True)
@click.option('--units', '-u', help=' Text for the units system in which the model '
              'geometry exists. Must be (Meters, Millimeters, Feet, Inches, '
              'Centimeters).', type=str, default='Meters', show_default=True)
@click.option('--tolerance', '-t', help='The maximum difference between x, y, and z '
              'values at which vertices are considered equivalent.',
              type=float, default=None)
@click.option('--output-file', '-f', help='Optional file to output the Model JSON '
              'string. By default it will be printed out to stdout',
              type=click.File('w'), default='-')
def shoe_box(width, depth, height, orientation_angle, window_ratio, adiabatic,
             units, tolerance, output_file):
    """Create a model with a single shoe box Room.

    \b
    Args:
        width: Number for the width of the box (in the X direction).
        depth: Number for the depth of the box (in the Y direction).
        height: Number for the height of the box (in the Z direction).
    """
    try:
        # create the model object
        model = Model.from_shoe_box(
            width, depth, height, orientation_angle, window_ratio,
            adiabatic, units, tolerance)
        # write the model out to the file or stdout
        output_file.write(json.dumps(model.to_dict()))
    except Exception as e:
        _logger.exception('Shoe box creation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@create.command('rectangle-plan')
@click.argument('width', type=float)
@click.argument('length', type=float)
@click.argument('floor-to-floor-height', type=float)
@click.option('--perimeter-offset', '-p', help='An optional positive number that will '
              'be used to offset the perimeter to create core/perimeter Rooms. '
              'If this value is 0, no offset will occur and each floor will have one '
              'Room', type=float, default=0, show_default=True)
@click.option('--story-count', '-s', help='An integer for the number of stories to '
              'generate.', type=int, default=1, show_default=True)
@click.option('--orientation-angle', '-a', help='A number between 0 and 360 for the '
              'counterclockwise orientation that the width of the box faces.',
              type=float, default=0, show_default=True)
@click.option('--outdoor-roof/--adiabatic-roof', ' /-ar', help='Flag to note whether '
              'the roof faces of the top floor should be outdoor or adiabatic.',
              default=True, show_default=True)
@click.option('--ground-floor/--adiabatic-floor', ' /-af', help='Flag to note whether '
              'the floor faces of the bottom floor should be ground or adiabatic.',
              default=True, show_default=True)
@click.option('--units', '-u', help=' Text for the units system in which the model '
              'geometry exists. Must be (Meters, Millimeters, Feet, Inches, '
              'Centimeters).', type=str, default='Meters', show_default=True)
@click.option('--tolerance', '-t', help='The maximum difference between x, y, and z '
              'values at which vertices are considered equivalent.',
              type=float, default=None)
@click.option('--output-file', '-f', help='Optional file to output the Model JSON '
              'string. By default it will be printed out to stdout',
              type=click.File('w'), default='-')
def rectangle_plan(width, length, floor_to_floor_height, perimeter_offset, story_count,
                   orientation_angle, outdoor_roof, ground_floor, units, tolerance,
                   output_file):
    """Create a model with a rectangular floor plan.

    Note that the resulting Rooms in the model won't have any windows or solved
    adjacencies. The edit commands should be used for this purpose.

    \b
    Args:
        width: Number for the width of the plan (in the X direction).
        length: Number for the length of the plan (in the Y direction).
        floor_to_floor_height: Number for the height of each floor of the model
            (in the Z direction).
    """
    try:
        # create the model object
        model = Model.from_rectangle_plan(
            width, length, floor_to_floor_height, perimeter_offset, story_count,
            orientation_angle, outdoor_roof, ground_floor, units, tolerance)
        # write the model out to the file or stdout
        output_file.write(json.dumps(model.to_dict()))
    except Exception as e:
        _logger.exception('Rectangle plan model creation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@create.command('l-shaped-plan')
@click.argument('width-1', type=float)
@click.argument('length-1', type=float)
@click.argument('width-2', type=float)
@click.argument('length-2', type=float)
@click.argument('floor-to-floor-height', type=float)
@click.option('--perimeter-offset', '-p', help='An optional positive number that will be'
              ' used  to offset the perimeter to create core/perimeter Rooms. '
              'If this value is 0, no offset will occur and each floor will have one '
              'Room', type=float, default=0, show_default=True)
@click.option('--story-count', '-s', help='An integer for the number of stories to '
              'generate.', type=int, default=1, show_default=True)
@click.option('--orientation-angle', '-a', help='A number between 0 and 360 for the '
              'counterclockwise orientation that the L faces.',
              type=float, default=0, show_default=True)
@click.option('--outdoor-roof/--adiabatic-roof', ' /-ar', help='Flag to note whether '
              'the roof faces of the top floor should be outdoor or adiabatic.',
              default=True, show_default=True)
@click.option('--ground-floor/--adiabatic-floor', ' /-af', help='Flag to note whether '
              'the floor faces of the bottom floor should be ground or adiabatic.',
              default=True, show_default=True)
@click.option('--units', '-u', help=' Text for the units system in which the model '
              'geometry exists. Must be (Meters, Millimeters, Feet, Inches, '
              'Centimeters).', type=str, default='Meters', show_default=True)
@click.option('--tolerance', '-t', help='The maximum difference between x, y, and z '
              'values at which vertices are considered equivalent.',
              type=float, default=None)
@click.option('--output-file', '-f', help='Optional file to output the Model JSON '
              'string. By default it will be printed out to stdout',
              type=click.File('w'), default='-')
def l_shaped_plan(width_1, length_1, width_2, length_2, floor_to_floor_height,
                  perimeter_offset, story_count, orientation_angle, outdoor_roof,
                  ground_floor, units, tolerance, output_file):
    """Create a model with an L-shaped floor plan.

    Note that the resulting Rooms in the model won't have any windows or solved
    adjacencies. The edit commands should be used for this purpose.

    \b
    Args:
        width_1: Number for the width of the lower part of the L segment.
        length_1: Number for the length of the lower part of the L segment, not
            counting the overlap between the upper and lower segments.
        width_2: Number for the width of the upper (left) part of the L segment.
        length_2: Number for the length of the upper (left) part of the L segment, not
            counting the overlap between the upper and lower segments.
        floor_to_floor_height: Number for the height of each floor of the model
            (in the Z direction).
    """
    try:
        # create the model object
        model = Model.from_l_shaped_plan(
            width_1, length_1, width_2, length_2, floor_to_floor_height,
            perimeter_offset, story_count, orientation_angle, outdoor_roof, ground_floor,
            units, tolerance)
        # write the model out to the file or stdout
        output_file.write(json.dumps(model.to_dict()))
    except Exception as e:
        _logger.exception('L Shaped plan model creation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@create.command('from-sync')
@click.argument('base-model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('other-model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('sync-instructions-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--output-file', '-f', help='Optional file to output the Model JSON '
    'string. By default it will be printed out to stdout',
    type=click.File('w'), default='-')
def create_from_sync(
        base_model_file, other_model_file, sync_instructions_file, output_file):
    """Create a Model from two similar model files and instructions for syncing them.

    \b
    Args:
        base_model_file: An base Honeybee Model (as HBJSON or HBPkl)
            that forms the base of the new model to be created.
        other_model_file: An other Honeybee Model (as HBJSON or HBPkl)
            that contains changes to the base model to be merged into
            the base_model.
        sync_instructions: A JSON file of SyncInstructions that states which
            changes from the other model should be accepted or rejected
            when building a new Model from the base model. The SyncInstructions
            schema is essentially a variant of the ComparisonReport schema
            that can be obtained by calling `honeybee compare models base_model_file
            other_model_file --json`. The main difference is that the XXX_changed
            properties should be replaced with update_XXX properties for
            whether the change from the other_model should be accepted into
            the new model or rejected from it.
    """
    try:
        new_model = Model.from_sync_files(
            base_model_file, other_model_file, sync_instructions_file)
        output_file.write(json.dumps(new_model.to_dict()))
    except Exception as e:
        _logger.exception('Model from sync failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)
