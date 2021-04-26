"""honeybee model editing commands."""
import click
import sys
import logging
import json

from ladybug_geometry.geometry2d.pointvector import Vector2D
from ladybug_geometry.geometry3d.pointvector import Vector3D

from honeybee.model import Model
from honeybee.room import Room
from honeybee.units import parse_distance_string
from honeybee.facetype import face_types, Wall
from honeybee.boundarycondition import Outdoors
from honeybee.boundarycondition import boundary_conditions as bcs
try:
    ad_bc = bcs.adiabatic
except AttributeError:  # honeybee_energy is not loaded and adiabatic does not exist
    ad_bc = None

_logger = logging.getLogger(__name__)


@click.group(help='Commands for editing Honeybee models.')
def edit():
    pass


@edit.command('convert-units')
@click.argument('model-json', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('units', type=str)
@click.option('--scale/--do-not-scale', ' /-ns', help='Flag to note whether the model '
              'should be scaled as it is converted to the new units system.',
              default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the Model JSON string'
              ' with solved adjacency. By default it will be printed out to stdout',
              type=click.File('w'), default='-')
def convert_units(model_json, units, scale, output_file):
    """Convert a Model to a given units system.

    \b
    Args:
        model_json: Full path to a Honeybee Model JSON file.
        units: Text for the units system to which the model will be converted.
            Choose from (Meters, Millimeters, Feet, Inches, Centimeters).
    """
    try:
        parsed_model = Model.from_file(model_json)
        if scale:
            parsed_model.convert_to_units(units)
        else:
            parsed_model.units = units
        # write the new model out to the file or stdout
        output_file.write(json.dumps(parsed_model.to_dict()))
    except Exception as e:
        _logger.exception('Model unit conversion failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@edit.command('solve-adjacency')
@click.argument('model-json', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--wall/--air-boundary', ' /-ab', help='Flag to note whether the '
              'wall adjacencies should be of the air boundary face type.',
              default=True, show_default=True)
@click.option('--surface/--adiabatic', ' /-a', help='Flag to note whether the '
              'adjacencies should be surface or adiabatic.',
              default=True, show_default=True)
@click.option('--no-overwrite/--overwrite', ' /-ow', help='Flag to note whether existing'
              ' Surface boundary conditions should be overwritten.',
              default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the Model JSON string'
              ' with solved adjacency. By default it will be printed out to stdout',
              type=click.File('w'), default='-')
def solve_adjacency(model_json, wall, surface, no_overwrite, output_file):
    """Solve adjacency between Rooms of a Model JSON file.

    \b
    Args:
        model_json: Full path to a Honeybee Model JSON file.
    """
    try:
        # serialize the Model to Python and check the tolerance
        parsed_model = Model.from_file(model_json)
        assert parsed_model.tolerance != 0, \
            'Model must have a non-zero tolerance to use solve-adjacency.'
        tol = parsed_model.tolerance

        # solve adjacency
        if no_overwrite:  # only assign new adjacencies
            adj_info = Room.solve_adjacency(parsed_model.rooms, tol)
        else:  # overwrite existing Surface BC
            adj_faces = Room.find_adjacency(parsed_model.rooms, tol)
            for face_pair in adj_faces:
                face_pair[0].set_adjacency(face_pair[1])
            adj_info = {'adjacent_faces': adj_faces}

        # try to assign the air boundary face type
        if not wall:
            for face_pair in adj_info['adjacent_faces']:
                if isinstance(face_pair[0].type, Wall):
                    face_pair[0].type = face_types.air_boundary
                    face_pair[1].type = face_types.air_boundary

        # try to assign the adiabatic boundary condition
        if not surface and ad_bc:
            for face_pair in adj_info['adjacent_faces']:
                face_pair[0].boundary_condition = ad_bc
                face_pair[1].boundary_condition = ad_bc

        # write the new model out to the file or stdout
        output_file.write(json.dumps(parsed_model.to_dict()))
    except Exception as e:
        _logger.exception('Model solve adjacency failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@edit.command('windows-by-ratio')
@click.argument('model-json', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('ratio', type=float)
@click.option('--output-file', '-f', help='Optional file to output the Model JSON string'
              ' with windows. By default it will be printed out to stdout',
              type=click.File('w'), default='-')
def windows_by_ratio(model_json, ratio, output_file):
    """Add apertures to all outdoor walls of a model given a ratio.

    Note that this method removes any existing apertures and doors from the Walls.
    This method attempts to generate as few apertures as necessary to meet the ratio.

    \b
    Args:
        model_json: Full path to a Honeybee Model JSON file.
        ratio: A number between 0 and 1 (but not perfectly equal to 1)
            for the desired ratio between window area and wall area.
    """
    try:
        # serialize the Model and check the Model tolerance
        parsed_model = Model.from_file(model_json)
        assert parsed_model.tolerance != 0, \
            'Model must have a non-zero tolerance to use windows-by-ratio.'
        tol = parsed_model.tolerance

        # generate the windows for all walls of rooms
        for room in parsed_model.rooms:
            for face in room.faces:
                if isinstance(face.boundary_condition, Outdoors) and \
                        isinstance(face.type, Wall):
                    face.apertures_by_ratio(ratio, tol)

        # write the new model out to the file or stdout
        output_file.write(json.dumps(parsed_model.to_dict()))
    except Exception as e:
        _logger.exception('Model windows by ratio failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@edit.command('windows-by-ratio-rect')
@click.argument('model-json', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('ratio', type=float)
@click.option('--aperture-height', '-ah', help='A number for the target height of the '
              'output apertures. This can include the units of the distance (eg. 3ft) '
              'or, if no units are provided the value will be interpreted in the '
              'honeybee model units. Note that, if the ratio is too large for the '
              'height, the ratio will take precedence and the actual aperture_height '
              'will be larger than this value.',
              type=str, default='2m', show_default=True)
@click.option('--sill-height', '-sh', help='A number for the target height above the '
              'bottom edge of the rectangle to start the apertures. Note that, if the '
              'ratio is too large for the height, the ratio will take precedence '
              'and the sill_height will be smaller than this value. This can include '
              'the units of the distance (eg. 3ft) or, if no units are provided, '
              'the value will be interpreted in the honeybee model units.',
              type=str, default='0.8m', show_default=True)
@click.option('--horizontal-separation', '-hs', help='A number for the target '
              'separation between individual aperture centerlines. If this number is '
              'larger than the parent rectangle base, only one aperture will be '
              'produced. This can include the units of the distance (eg. 3ft) or, if '
              'no units are provided, the value will be interpreted in the honeybee '
              'model units.', type=str, default='3m', show_default=True)
@click.option('--vertical-separation', '-vs', help='An optional number to create a '
              'single vertical separation between top and bottom apertures. This can '
              'include the units of the distance (eg. 3ft) or, if no units are provided '
              'the value will be interpreted in the honeybee model units.',
              type=str, default='0', show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the Model JSON string'
              ' with windows. By default it will be printed out to stdout',
              type=click.File('w'), default='-')
def windows_by_ratio_rect(model_json, ratio, aperture_height, sill_height,
                          horizontal_separation, vertical_separation, output_file):
    """Add apertures to all outdoor walls of a model given a ratio.

    Note that this method removes any existing apertures and doors from the Walls.
    Any rectangular portions of walls will have customized rectangular apertures
    using the various inputs.

    \b
    Args:
        model_json: Full path to a Honeybee Model JSON file.
        ratio: A number between 0 and 1 (but not perfectly equal to 1)
            for the desired ratio between window area and wall area.
    """
    try:
        # serialize the Model and check the Model tolerance
        parsed_model = Model.from_file(model_json)
        assert parsed_model.tolerance != 0, \
            'Model must have a non-zero tolerance to use windows-by-ratio-rect.'
        tol, units = parsed_model.tolerance, parsed_model.units

        # convert distance strings to floats
        aperture_height = parse_distance_string(aperture_height, units)
        sill_height = parse_distance_string(sill_height, units)
        horizontal_separation = parse_distance_string(horizontal_separation, units)
        vertical_separation = parse_distance_string(vertical_separation, units)

        # generate the windows for all walls of rooms
        for room in parsed_model.rooms:
            for face in room.faces:
                if isinstance(face.boundary_condition, Outdoors) and \
                        isinstance(face.type, Wall):
                    face.apertures_by_ratio_rectangle(
                        ratio, aperture_height, sill_height, horizontal_separation,
                        vertical_separation, tol)

        # write the new model out to the file or stdout
        output_file.write(json.dumps(parsed_model.to_dict()))
    except Exception as e:
        _logger.exception('Model windows by ratio rect failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@edit.command('extruded-border')
@click.argument('model-json', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--depth', '-d', help='A number for the extrusion depth. This can include '
              'the units of the distance (eg. 3ft) or, if no units are provided, '
              'the value will be interpreted in the honeybee model units.',
              type=str, default='0.2m', show_default=True)
@click.option('--outdoor/--indoor', ' /-i', help='Flag to note whether the borders '
              'should be on the indoors.', default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the Model JSON string'
              ' with borders. By default it will be printed out to stdout',
              type=click.File('w'), default='-')
def extruded_border(model_json, depth, outdoor, output_file):
    """Add extruded borders to all windows in walls.

    \b
    Args:
        model_json: Full path to a Honeybee Model JSON file.
    """
    try:
        # serialize the Model to Python
        parsed_model = Model.from_file(model_json)
        indoor = not outdoor

        # generate the overhangs for all walls of rooms
        depth = parse_distance_string(depth, parsed_model.units)
        for room in parsed_model.rooms:
            for face in room.faces:
                if isinstance(face.boundary_condition, Outdoors) and \
                        isinstance(face.type, Wall):
                    for ap in face.apertures:
                        ap.extruded_border(depth, indoor)

        # write the new model out to the file or stdout
        output_file.write(json.dumps(parsed_model.to_dict()))
    except Exception as e:
        _logger.exception('Model extruded border failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@edit.command('overhang')
@click.argument('model-json', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--depth', '-d', help='A number for the overhang depth. This can include '
              'the units of the distance (eg. 3ft) or, if no units are provided, '
              'the value will be interpreted in the honeybee model units.',
              type=str, default='1m', show_default=True)
@click.option('--angle', '-a', help='A number for the for an angle to rotate the '
              'overhang in degrees. Positive numbers indicate a downward rotation while '
              'negative numbers indicate an upward rotation.',
              type=float, default=0, show_default=True)
@click.option('--vertical-offset', '-vo', help='An optional number for the vertical '
              'offset of the overhang from the top of the window or face. Positive '
              'numbers move up while negative mode down. This can include '
              'the units of the distance (eg. 3ft) or, if no units are provided, '
              'the value will be interpreted in the honeybee model units.',
              type=str, default='0', show_default=True)
@click.option('--per-window/--per-wall', ' /-pw', help='Flag to note whether the '
              'overhangs should be generated per aperture or per wall.',
              default=True, show_default=True)
@click.option('--outdoor/--indoor', ' /-i', help='Flag to note whether the overhangs '
              'should be on the indoors like a light shelf.',
              default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the Model JSON string'
              ' with overhangs. By default it will be printed out to stdout',
              type=click.File('w'), default='-')
def overhang(model_json, depth, angle, vertical_offset, per_window, outdoor,
             output_file):
    """Add overhangs to all outdoor walls or windows in walls.

    \b
    Args:
        model_json: Full path to a Honeybee Model JSON file.
    """
    try:
        # serialize the Model to Python and check the Model tolerance
        parsed_model = Model.from_file(model_json)
        assert parsed_model.tolerance != 0, \
            'Model must have a non-zero tolerance to use overhang.'
        tol, units = parsed_model.tolerance, parsed_model.units
        indoor = not outdoor

        # generate the overhangs for all walls of rooms
        depth = parse_distance_string(depth, units)
        overhangs = []
        for room in parsed_model.rooms:
            for face in room.faces:
                if isinstance(face.boundary_condition, Outdoors) and \
                        isinstance(face.type, Wall):
                    if per_window:
                        for ap in face.apertures:
                            overhangs.extend(ap.overhang(depth, angle, indoor, tol))
                    else:
                        overhangs.extend(face.overhang(depth, angle, indoor, tol))

        # move the overhangs if an offset has been specified
        vertical_offset = parse_distance_string(vertical_offset, units)
        if vertical_offset != 0:
            m_vec = Vector3D(0, 0, vertical_offset)
            for shd in overhangs:
                shd.move(m_vec)

        # write the new model out to the file or stdout
        output_file.write(json.dumps(parsed_model.to_dict()))
    except Exception as e:
        _logger.exception('Model overhang failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@edit.command('louvers-by-count')
@click.argument('model-json', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('louver-count', type=int)
@click.option('--depth', '-d', help='A number for the depth of the louvers. This can '
              'include the units of the distance (eg. 1ft) or, if no units are '
              'provided, the value will be interpreted in the honeybee model units.',
              type=str, default='0.25m', show_default=True)
@click.option('--angle', '-a', help='A number for the for an angle to rotate the '
              'louvers in degrees. Positive numbers indicate a downward rotation while '
              'negative numbers indicate an upward rotation.',
              type=float, default=0, show_default=True)
@click.option('--offset', '-o', help='An optional number for the offset of the louvers '
              'from base Face or Aperture. This can include the units of the distance '
              '(eg. 1ft) or, if no units are provided, the value will be interpreted in '
              'the honeybee model units.', type=str, default='0', show_default=True)
@click.option('--horizontal/--vertical', ' /-v', help='Flag to note whether louvers '
              'are horizontal or vertical.', default=True, show_default=True)
@click.option('--per-window/--per-wall', ' /-pw', help='Flag to note whether the '
              'louvers should be generated per aperture or per wall.',
              default=True, show_default=True)
@click.option('--outdoor/--indoor', ' /-i', help='Flag to note whether the louvers '
              'should be on the indoors like a light shelf.',
              default=True, show_default=True)
@click.option('--no-flip/--flip-start', ' /-fs', help='Flag to note whether the '
              'the side that the louvers start from should be flipped. If not flipped, '
              'louvers will start from top or right. If flipped, they will start from '
              'the bottom or left.', default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the Model JSON string'
              ' with louvers. By default it will be printed out to stdout',
              type=click.File('w'), default='-')
def louvers_by_count(model_json, louver_count, depth, angle, offset, horizontal,
                     per_window, outdoor, no_flip, output_file):
    """Add louvers to all outdoor walls or windows in walls.

    \b
    Args:
        model_json: Full path to a Honeybee Model JSON file.
        louver_count: A positive integer for the number of louvers to generate.
    """
    try:
        # serialize the Model and check the Model tolerance
        parsed_model = Model.from_file(model_json)
        assert parsed_model.tolerance != 0, \
            'Model must have a non-zero tolerance to use overhang.'
        tol, units = parsed_model.tolerance, parsed_model.units
        indoor = not outdoor
        flip_start = not no_flip
        cont_vec = Vector2D(0, 1) if horizontal else Vector2D(1, 0)

        # generate the overhangs for all walls of rooms
        depth = parse_distance_string(depth, units)
        offset = parse_distance_string(offset, units)
        for room in parsed_model.rooms:
            for face in room.faces:
                if isinstance(face.boundary_condition, Outdoors) and \
                        isinstance(face.type, Wall):
                    if per_window:
                        for ap in face.apertures:
                            ap.louvers_by_count(louver_count, depth, offset, angle,
                                                cont_vec, flip_start, indoor, tol)
                    else:
                        face.louvers_by_count(louver_count, depth, offset, angle,
                                              cont_vec, flip_start, indoor, tol)

        # write the new model out to the file or stdout
        output_file.write(json.dumps(parsed_model.to_dict()))
    except Exception as e:
        _logger.exception('Model louver generation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@edit.command('louvers-by-spacing')
@click.argument('model-json', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--spacing', '-s', help='A number for the distance between each louver. '
              'This can include the units of the distance (eg. 2ft) or, if no units are '
              'provided, the value will be interpreted in the honeybee model units.',
              type=str, default='0.5m', show_default=True)
@click.option('--depth', '-d', help='A number for the depth of the louvers. This can '
              'include the units of the distance (eg. 1ft) or, if no units are '
              'provided, the value will be interpreted in the honeybee model units.',
              type=str, default='0.25m', show_default=True)
@click.option('--angle', '-a', help='A number for the for an angle to rotate the '
              'louvers in degrees. Positive numbers indicate a downward rotation while '
              'negative numbers indicate an upward rotation.',
              type=float, default=0, show_default=True)
@click.option('--offset', '-o', help='An optional number for the offset of the louvers '
              'from base Face or Aperture. This can include the units of the distance '
              '(eg. 1ft) or, if no units are provided, the value will be interpreted in '
              'the honeybee model units.', type=str, default='0', show_default=True)
@click.option('--horizontal/--vertical', ' /-v', help='Flag to note wh.',
              default=True, show_default=True)
@click.option('--max-count', '-m', help='Optional integer to set the maximum number of '
              'louvers that will be generated. If 0, louvers will cover the entire '
              'face.', type=int, default=0, show_default=True)
@click.option('--per-window/--per-wall', ' /-pw', help='Flag to note whether the '
              'louvers should be generated per aperture or per wall.',
              default=True, show_default=True)
@click.option('--outdoor/--indoor', ' /-i', help='Flag to note whether the louvers '
              'should be on the indoors like a light shelf.',
              default=True, show_default=True)
@click.option('--no-flip/--flip-start', ' /-fs', help='Flag to note whether the '
              'the side that the louvers start from should be flipped. If not flipped, '
              'louvers will start from top or right. If flipped, they will start from '
              'the bottom or left.', default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the Model JSON string'
              ' with louvers. By default it will be printed out to stdout',
              type=click.File('w'), default='-')
def louvers_by_spacing(model_json, spacing, depth, angle, offset, horizontal,
                       max_count, per_window, outdoor, no_flip, output_file):
    """Add louvers to all outdoor walls or windows in walls.

    \b
    Args:
        model_json: Full path to a Honeybee Model JSON file.
    """
    try:
        # serialize the Model to Python and check the Model tolerance
        parsed_model = Model.from_file(model_json)
        assert parsed_model.tolerance != 0, \
            'Model must have a non-zero tolerance to use overhang.'
        tol, units = parsed_model.tolerance, parsed_model.units
        indoor = not outdoor
        flip_start = not no_flip
        cont_vec = Vector2D(0, 1) if horizontal else Vector2D(1, 0)

        # generate the overhangs for all walls of rooms
        spacing = parse_distance_string(spacing, units)
        depth = parse_distance_string(depth, units)
        offset = parse_distance_string(offset, units)
        for room in parsed_model.rooms:
            for face in room.faces:
                if isinstance(face.boundary_condition, Outdoors) and \
                        isinstance(face.type, Wall):
                    if per_window:
                        for ap in face.apertures:
                            ap.louvers_by_distance_between(
                                spacing, depth, offset, angle, cont_vec,
                                flip_start, indoor, tol, max_count)
                    else:
                        face.louvers_by_distance_between(
                            spacing, depth, offset, angle, cont_vec, flip_start,
                            indoor, tol, max_count)

        # write the new model out to the file or stdout
        output_file.write(json.dumps(parsed_model.to_dict()))
    except Exception as e:
        _logger.exception('Model louver generation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)
