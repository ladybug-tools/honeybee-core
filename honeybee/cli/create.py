"""honeybee model creation commands."""
import click
import sys
import logging
import json
import math
import uuid

from ladybug_geometry.geometry2d.pointvector import Point2D, Vector2D
from ladybug_geometry.geometry2d.polygon import Polygon2D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.geometry3d.polyface import Polyface3D
from ladybug_geometry_polyskel.polysplit import perimeter_core_subpolygons

from honeybee.model import Model
from honeybee.room import Room
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
              type=float, default=0.01, show_default=True)
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
        unique_id = str(uuid.uuid4())[:8]  # unique identifier for the shoe box

        # create the box room and assign all of the attributes
        room_id = 'Shoe_Box_Room_{}'.format(unique_id)
        room = Room.from_box(room_id, width, depth, height, orientation_angle)
        room.display_name = 'Shoe_Box_Room'
        front_face = room[1]
        front_face.apertures_by_ratio(window_ratio, tolerance)
        if adiabatic and ad_bc:
            room[0].boundary_condition = ad_bc  # make the floor adiabatic
            for face in room[2:]:  # make all other face adiabatic
                face.boundary_condition = ad_bc

        # create the model object
        model_id = 'Shoe_Box_Model_{}'.format(unique_id)
        model = Model(model_id, [room], units=units,
                      tolerance=tolerance, angle_tolerance=1)

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
@click.option('--perimeter-offset', '-p', help='An optional positive number that will be'
              ' used  to offset the perimeter to create core/perimeter Rooms. '
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
              type=float, default=0.01, show_default=True)
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
        # create the geometry of the rooms for the first floor
        footprint = [Face3D.from_rectangle(width, length)]
        if perimeter_offset != 0:  # use the straight skeleton methods
            assert perimeter_offset > 0, 'perimeter_offset cannot be less than than 0.'
            try:
                footprint = []
                base = Polygon2D.from_rectangle(Point2D(), Vector2D(0, 1), width, length)
                sub_polys_perim, sub_polys_core = perimeter_core_subpolygons(
                    polygon=base, distance=perimeter_offset, tol=tolerance)
                for s_poly in sub_polys_perim + sub_polys_core:
                    sub_face = Face3D([Point3D(pt.x, pt.y, 0) for pt in s_poly])
                    footprint.append(sub_face)
            except RuntimeError:
                pass

        # create the honeybee rooms
        unique_id = str(uuid.uuid4())[:8]  # unique identifier for the model
        rm_ids = ['Room'] if len(footprint) == 1 else ['Front', 'Right', 'Back', 'Left']
        if len(footprint) == 5:
            rm_ids.append('Core')
        rooms = _rooms_from_footprint(
            footprint, rm_ids, unique_id, floor_to_floor_height, orientation_angle,
            story_count, outdoor_roof, ground_floor)

        # create the model object
        model_id = 'Rectangle_Plan_Model_{}'.format(unique_id)
        model = Model(model_id, rooms, units=units,
                      tolerance=tolerance, angle_tolerance=1)

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
              type=float, default=0.01, show_default=True)
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
        # create the geometry of the rooms for the first floor
        max_x, max_y = width_2 + length_1, width_1 + length_2
        pts = [(0, 0), (max_x, 0), (max_x, width_1), (width_2, width_1),
               (width_2, max_y), (0, max_y)]
        footprint = Face3D(tuple(Point3D(*pt) for pt in pts))
        if perimeter_offset != 0:  # use the straight skeleton methods
            assert perimeter_offset > 0, 'perimeter_offset cannot be less than than 0.'
            try:
                footprint = []
                base = Polygon2D(tuple(Point2D(*pt) for pt in pts))
                sub_polys_perim, sub_polys_core = perimeter_core_subpolygons(
                    polygon=base, distance=perimeter_offset, tol=tolerance)
                for s_poly in sub_polys_perim + sub_polys_core:
                    sub_face = Face3D([Point3D(pt.x, pt.y, 0) for pt in s_poly])
                    footprint.append(sub_face)
            except RuntimeError:
                pass

        # create the honeybee rooms
        unique_id = str(uuid.uuid4())[:8]  # unique identifier for the model
        rm_ids = ['Room'] if len(footprint) == 1 else \
            ['LongEdge1', 'End1', 'ShortEdge1', 'ShortEdge2', 'End2', 'LongEdge2']
        if len(footprint) == 7:
            rm_ids.append('Core')
        rooms = _rooms_from_footprint(
            footprint, rm_ids, unique_id, floor_to_floor_height, orientation_angle,
            story_count, outdoor_roof, ground_floor)

        # create the model object
        model_id = 'L_Shaped_Plan_Model_{}'.format(unique_id)
        model = Model(model_id, rooms, units=units,
                      tolerance=tolerance, angle_tolerance=1)

        # write the model out to the file or stdout
        output_file.write(json.dumps(model.to_dict()))
    except Exception as e:
        _logger.exception('L Shaped plan model creation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def _rooms_from_footprint(
        footprint, room_ids, unique_id, floor_to_floor_height, orientation_angle,
        story_count, outdoor_roof, ground_floor):
    """Function to convert footprint geometry into full honeybee rooms."""
    # extrude the footprint into solids
    first_floor = [Polyface3D.from_offset_face(geo, floor_to_floor_height)
                   for geo in footprint]

    # rotate the geometries if an orientation angle is specified
    if orientation_angle != 0:
        angle, origin = math.radians(orientation_angle), Point3D()
        first_floor = [geo.rotate_xy(angle, origin) for geo in first_floor]

    # create the initial rooms for the first floor
    rooms = []
    for polyface, rmid in zip(first_floor, room_ids):
        rooms.append(Room.from_polyface3d('{}_{}'.format(rmid, unique_id), polyface))

    # if there are multiple stories, duplicate the first floor rooms
    if story_count != 1:
        all_rooms = []
        for i in range(story_count):
            for room in rooms:
                new_room = room.duplicate()
                new_room.add_prefix('Floor{}'.format(i + 1))
                m_vec = Vector3D(0, 0, floor_to_floor_height * i)
                new_room.move(m_vec)
                all_rooms.append(new_room)
        rooms = all_rooms

    # assign readable names for the display_name (without the UUID)
    for room in rooms:
        room.display_name = room.identifier[:-9]

    # assign adiabatic boundary conditions if requested
    if not outdoor_roof and ad_bc:
        for room in rooms[-len(first_floor):]:
            room[-1].boundary_condition = ad_bc  # make the roof adiabatic
    if not ground_floor and ad_bc:
        for room in rooms[:len(first_floor)]:
            room[0].boundary_condition = ad_bc  # make the floor adiabatic
    return rooms
