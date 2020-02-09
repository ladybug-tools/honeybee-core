"""Test Model class."""
from honeybee.model import Model
from honeybee.room import Room
from honeybee.face import Face
from honeybee.shade import Shade
from honeybee.aperture import Aperture
from honeybee.door import Door
from honeybee.boundarycondition import Surface
from honeybee.facetype import face_types

from ladybug_geometry.geometry2d.pointvector import Vector2D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.plane import Plane
from ladybug_geometry.geometry3d.face import Face3D

import math
import pytest


def test_model_init():
    """Test the initialization of the Model and basic properties."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    north_face = room[1]
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1),
                      Point3D(2.5, 10, 2.5), Point3D(4.5, 10, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('Front Aperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)

    model = Model('Tiny House', [room])
    str(model)  # test the string representation of the object

    assert model.name == 'TinyHouse'
    assert model.display_name == 'Tiny House'
    assert model.north_angle == 0
    assert model.north_vector == Vector2D(0, 1)
    assert model.units == 'Meters'
    assert model.tolerance == 0
    assert model.angle_tolerance == 0
    assert len(model.rooms) == 1
    assert isinstance(model.rooms[0], Room)
    assert len(model.faces) == 6
    assert isinstance(model.faces[0], Face)
    assert len(model.shades) == 2
    assert isinstance(model.shades[0], Shade)
    assert len(model.apertures) == 2
    assert isinstance(model.apertures[0], Aperture)
    assert len(model.doors) == 1
    assert isinstance(model.doors[0], Door)
    assert len(model.orphaned_faces) == 0
    assert len(model.orphaned_shades) == 0
    assert len(model.orphaned_apertures) == 0
    assert len(model.orphaned_doors) == 0


def test_model_properties_setability():
    """Test the setting of properties on the Model."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)

    model = Model('Tiny House', [room])

    model.name = 'TestBox'
    assert model.name == 'TestBox'
    model.north_angle = 20
    assert model.north_angle == 20
    model.units = 'Feet'
    assert model.units == 'Feet'
    model.tolerance = 0.01
    assert model.tolerance == 0.01
    model.angle_tolerance = 0.01
    assert model.angle_tolerance == 0.01


def test_model_init_orphaned_objects():
    """Test the initialization of the Model with orphaned objects."""
    pts_1 = [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(10, 10, 0), Point3D(10, 0, 0)]
    pts_2 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(0, 10, 0)]
    pts_3 = [Point3D(0, 0, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(0, 0, 3)]
    pts_4 = [Point3D(10, 10, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(10, 10, 3)]
    pts_5 = [Point3D(10, 10, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(10, 10, 3)]
    pts_6 = [Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    face_1 = Face('Face 1', Face3D(pts_1))
    face_2 = Face('Face 2', Face3D(pts_2))
    face_3 = Face('Face 3', Face3D(pts_3))
    face_4 = Face('Face 4', Face3D(pts_4))
    face_5 = Face('Face 5', Face3D(pts_5))
    face_6 = Face('Face 6', Face3D(pts_6))
    face_2.apertures_by_ratio(0.4, 0.01)
    face_2.apertures[0].overhang(0.5, indoor=False)
    face_2.apertures[0].overhang(0.5, indoor=True)
    face_2.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    aperture_verts = [Point3D(4.5, 5, 1), Point3D(2.5, 5, 1),
                      Point3D(2.5, 5, 2.5), Point3D(4.5, 5, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    aperture = Aperture('Partition', Face3D(aperture_verts))
    table_geo = Face3D.from_rectangle(2, 2, Plane(o=Point3D(1.5, 4, 1)))
    table = Shade('Table', table_geo)
    tree_canopy_geo = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(5, -3, 4)))
    tree_canopy = Shade('Tree Canopy', tree_canopy_geo)

    model = Model('Tiny House', [], [face_1, face_2, face_3, face_4, face_5, face_6],
                  [table, tree_canopy], [aperture], [door])

    assert len(model.rooms) == 0
    assert len(model.faces) == 6
    assert isinstance(model.faces[0], Face)
    assert len(model.shades) == 4
    assert isinstance(model.shades[0], Shade)
    assert len(model.apertures) == 2
    assert isinstance(model.apertures[0], Aperture)
    assert len(model.doors) == 1
    assert isinstance(model.doors[0], Door)
    assert len(model.orphaned_faces) == 6
    assert len(model.orphaned_shades) == 2
    assert len(model.orphaned_apertures) == 1
    assert len(model.orphaned_doors) == 1


def test_adjacent_zone_model():
    """Test the solve adjacency method with an interior aperture."""
    room_south = Room.from_box('South Zone', 5, 5, 3, origin=Point3D(0, 0, 0))
    room_north = Room.from_box('North Zone', 5, 5, 3, origin=Point3D(0, 5, 0))
    room_south[1].apertures_by_ratio(0.4, 0.01)
    room_north[3].apertures_by_ratio(0.4, 0.01)

    room_south[3].apertures_by_ratio(0.4, 0.01)
    room_south[3].apertures[0].overhang(0.5, indoor=False)
    room_south[3].apertures[0].overhang(0.5, indoor=True)
    room_south[3].apertures[0].move_shades(Vector3D(0, 0, -0.5))
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1),
                      Point3D(2.5, 10, 2.5), Point3D(4.5, 10, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    room_north[1].add_door(door)
    aperture = Aperture('Front Aperture', Face3D(aperture_verts))
    room_north[1].add_aperture(aperture)
    Room.solve_adjacency([room_south, room_north], 0.01)

    model = Model('Two Room House', [room_south, room_north])

    assert len(model.rooms) == 2
    assert len(model.faces) == 12
    assert len(model.shades) == 2
    assert len(model.apertures) == 4
    assert len(model.doors) == 1

    model_dict = model.to_dict()
    new_model = Model.from_dict(model_dict)

    assert isinstance(new_model.rooms[0][1].apertures[0].boundary_condition, Surface)
    assert isinstance(new_model.rooms[1][3].apertures[0].boundary_condition, Surface)
    assert new_model.rooms[0][1].apertures[0].boundary_condition.boundary_condition_object == \
        new_model.rooms[1][3].apertures[0].name
    assert new_model.rooms[1][3].apertures[0].boundary_condition.boundary_condition_object == \
        new_model.rooms[0][1].apertures[0].name


def test_model_init_from_objects():
    """Test the initialization of the Model from_objects."""
    pts_1 = [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(10, 10, 0), Point3D(10, 0, 0)]
    pts_2 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(0, 10, 0)]
    pts_3 = [Point3D(0, 0, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(0, 0, 3)]
    pts_4 = [Point3D(10, 10, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(10, 10, 3)]
    pts_5 = [Point3D(10, 10, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(10, 10, 3)]
    pts_6 = [Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    face_1 = Face('Face 1', Face3D(pts_1))
    face_2 = Face('Face 2', Face3D(pts_2))
    face_3 = Face('Face 3', Face3D(pts_3))
    face_4 = Face('Face 4', Face3D(pts_4))
    face_5 = Face('Face 5', Face3D(pts_5))
    face_6 = Face('Face 6', Face3D(pts_6))
    face_2.apertures_by_ratio(0.4, 0.01)
    face_2.apertures[0].overhang(0.5, indoor=False)
    face_2.apertures[0].overhang(0.5, indoor=True)
    face_2.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    aperture_verts = [Point3D(4.5, 5, 1), Point3D(2.5, 5, 1),
                      Point3D(2.5, 5, 2.5), Point3D(4.5, 5, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    aperture = Aperture('Partition', Face3D(aperture_verts))
    table_geo = Face3D.from_rectangle(2, 2, Plane(o=Point3D(1.5, 4, 1)))
    table = Shade('Table', table_geo)
    tree_canopy_geo = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(5, -3, 4)))
    tree_canopy = Shade('Tree Canopy', tree_canopy_geo)

    model = Model.from_objects(
        'Tiny House', [face_1, face_2, face_3, face_4, face_5, face_6,
                       table, tree_canopy, aperture, door])

    assert len(model.rooms) == 0
    assert len(model.faces) == 6
    assert isinstance(model.faces[0], Face)
    assert len(model.shades) == 4
    assert isinstance(model.shades[0], Shade)
    assert len(model.apertures) == 2
    assert isinstance(model.apertures[0], Aperture)
    assert len(model.doors) == 1
    assert isinstance(model.doors[0], Door)
    assert len(model.orphaned_faces) == 6
    assert len(model.orphaned_shades) == 2
    assert len(model.orphaned_apertures) == 1
    assert len(model.orphaned_doors) == 1


def test_get_rooms_by_name():
    """Test the get_rooms_by_name method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    model = Model('Tiny House', [room])

    assert len(model.get_rooms_by_name(['TinyHouseZone'])) == 1
    with pytest.raises(ValueError):
        model.get_rooms_by_name(['NotARoom'])


def test_get_faces_by_name():
    """Test the get_faces_by_name method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    model = Model('Tiny House', [room])

    assert len(
        model.get_faces_by_name(['TinyHouseZone_Front', 'TinyHouseZone_Back'])) == 2
    with pytest.raises(ValueError):
        model.get_faces_by_name(['NotAFace'])


def test_get_shades_by_name():
    """Test the get_shades_by_name method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    model = Model('Tiny House', [room])

    assert len(model.get_shades_by_name(['TinyHouseZone_Back_Glz0_OutOverhang0'])) == 1
    with pytest.raises(ValueError):
        model.get_shades_by_name(['NotAShade'])


def test_get_apertures_by_name():
    """Test the get_apertures_by_name method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    model = Model('Tiny House', [room])

    assert len(model.get_apertures_by_name(['TinyHouseZone_Back_Glz0'])) == 1
    with pytest.raises(ValueError):
        model.get_apertures_by_name(['NotAnAperture'])


def test_get_doors_by_name():
    """Test the get_doors_by_name method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    north_face = room[1]
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    north_face.add_door(door)
    model = Model('Tiny House', [room])

    assert len(model.get_doors_by_name(['FrontDoor'])) == 1
    with pytest.raises(ValueError):
        model.get_doors_by_name(['NotADoor'])


def test_move():
    """Test the Model move method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    north_face = room[1]
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1),
                      Point3D(2.5, 10, 2.5), Point3D(4.5, 10, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('Front Aperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)

    new_room = room.duplicate()
    model = Model('Tiny House', [new_room])

    vec_1 = Vector3D(2, 2, 0)
    model.move(vec_1)

    assert room.center == \
        model.rooms[0].center.move(Vector3D(-2, -2, 0))
    assert south_face.apertures[0].indoor_shades[0].center == \
        model.rooms[0][3].apertures[0].indoor_shades[0].center.move(Vector3D(-2, -2, 0))
    assert south_face.apertures[0].outdoor_shades[0].center == \
        model.rooms[0][3].apertures[0].outdoor_shades[0].center.move(Vector3D(-2, -2, 0))
    assert room[3].apertures[0].center == \
        model.rooms[0][3].apertures[0].center.move(Vector3D(-2, -2, 0))
    assert room[1].doors[0].center == \
        model.rooms[0][1].doors[0].center.move(Vector3D(-2, -2, 0))

    assert room.floor_area == model.rooms[0].floor_area
    assert room.volume == model.rooms[0].volume
    assert south_face.apertures[0].indoor_shades[0].area == \
        model.rooms[0][3].apertures[0].indoor_shades[0].area
    assert south_face.apertures[0].outdoor_shades[0].area == \
        model.rooms[0][3].apertures[0].outdoor_shades[0].area
    assert room[3].apertures[0].area == model.rooms[0][3].apertures[0].area
    assert room[1].doors[0].area == model.rooms[0][1].doors[0].area


def test_scale():
    """Test the Model scale method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    north_face = room[1]
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1),
                      Point3D(2.5, 10, 2.5), Point3D(4.5, 10, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('Front Aperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)

    new_room = room.duplicate()
    model = Model('Tiny House', [new_room])
    model.scale(0.5)

    assert room.floor_area == model.rooms[0].floor_area * 2 ** 2
    assert room.volume == model.rooms[0].volume * 2 ** 3
    assert south_face.apertures[0].indoor_shades[0].area == \
        model.rooms[0][3].apertures[0].indoor_shades[0].area * 2 ** 2
    assert south_face.apertures[0].outdoor_shades[0].area == \
        model.rooms[0][3].apertures[0].outdoor_shades[0].area * 2 ** 2
    assert room[3].apertures[0].area == model.rooms[0][3].apertures[0].area * 2 ** 2
    assert room[1].doors[0].area == model.rooms[0][1].doors[0].area * 2 ** 2


def test_convert_to_units():
    """Test the Model convert_to_units method."""
    room = Room.from_box('Tiny House Zone', 120, 240, 96)
    inches_conversion = Model.conversion_factor_to_meters('Inches')

    model = Model('Tiny House', [room], units='Inches')
    model.convert_to_units('Meters')

    assert room.floor_area == pytest.approx(120 * 240 * (inches_conversion ** 2), rel=1e-3)
    assert room.volume == pytest.approx(120 * 240 * 96 * (inches_conversion ** 3), rel=1e-3)
    assert model.units == 'Meters'


def test_rotate():
    """Test the Model rotate method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    north_face = room[1]
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1),
                      Point3D(2.5, 10, 2.5), Point3D(4.5, 10, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('Front Aperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)

    new_room = room.duplicate()
    model = Model('Tiny House', [new_room])
    origin = Point3D(0, 0, 0)
    axis = Vector3D(1, 0, 0)
    model.rotate(axis, 90, origin)

    r_cent = model.rooms[0].center.rotate(axis, math.radians(-90), origin)
    assert room.center.x == pytest.approx(r_cent.x, rel=1e-3)
    assert room.center.y == pytest.approx(r_cent.y, rel=1e-3)
    assert room.center.z == pytest.approx(r_cent.z, rel=1e-3)
    shd_cent = model.rooms[0][3].apertures[0].outdoor_shades[0].center.rotate(axis, math.radians(-90), origin)
    assert south_face.apertures[0].outdoor_shades[0].center.x == pytest.approx(shd_cent.x, rel=1e-3)
    assert south_face.apertures[0].outdoor_shades[0].center.y == pytest.approx(shd_cent.y, rel=1e-3)
    assert south_face.apertures[0].outdoor_shades[0].center.z == pytest.approx(shd_cent.z, rel=1e-3)
    a_cent = model.rooms[0][3].apertures[0].center.rotate(axis, math.radians(-90), origin)
    assert room[3].apertures[0].center.x == pytest.approx(a_cent.x, rel=1e-3)
    assert room[3].apertures[0].center.y == pytest.approx(a_cent.y, rel=1e-3)
    assert room[3].apertures[0].center.z == pytest.approx(a_cent.z, rel=1e-3)
    d_cent = model.rooms[0][1].doors[0].center.rotate(axis, math.radians(-90), origin)
    assert room[1].doors[0].center.x == pytest.approx(d_cent.x, rel=1e-3)
    assert room[1].doors[0].center.y == pytest.approx(d_cent.y, rel=1e-3)
    assert room[1].doors[0].center.z == pytest.approx(d_cent.z, rel=1e-3)


def test_rotate_xy():
    """Test the Model rotate_xy method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    north_face = room[1]
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1),
                      Point3D(2.5, 10, 2.5), Point3D(4.5, 10, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('Front Aperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)

    new_room = room.duplicate()
    model = Model('Tiny House', [new_room])
    origin = Point3D(0, 0, 0)
    model.rotate_xy(90, origin)

    r_cent = model.rooms[0].center.rotate_xy(math.radians(-90), origin)
    assert room.center.x == pytest.approx(r_cent.x, rel=1e-3)
    assert room.center.y == pytest.approx(r_cent.y, rel=1e-3)
    assert room.center.z == pytest.approx(r_cent.z, rel=1e-3)
    shd_cent = model.rooms[0][3].apertures[0].shades[0].center.rotate_xy(math.radians(-90), origin)
    assert room[3].apertures[0].shades[0].center.x == pytest.approx(shd_cent.x, rel=1e-3)
    assert room[3].apertures[0].shades[0].center.y == pytest.approx(shd_cent.y, rel=1e-3)
    assert room[3].apertures[0].shades[0].center.z == pytest.approx(shd_cent.z, rel=1e-3)
    a_cent = model.rooms[0][3].apertures[0].center.rotate_xy(math.radians(-90), origin)
    assert room[3].apertures[0].center.x == pytest.approx(a_cent.x, rel=1e-3)
    assert room[3].apertures[0].center.y == pytest.approx(a_cent.y, rel=1e-3)
    assert room[3].apertures[0].center.z == pytest.approx(a_cent.z, rel=1e-3)
    d_cent = model.rooms[0][1].doors[0].center.rotate_xy(math.radians(-90), origin)
    assert room[1].doors[0].center.x == pytest.approx(d_cent.x, rel=1e-3)
    assert room[1].doors[0].center.y == pytest.approx(d_cent.y, rel=1e-3)
    assert room[1].doors[0].center.z == pytest.approx(d_cent.z, rel=1e-3)


def test_reflect():
    """Test the Model reflect method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    north_face = room[1]
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1),
                      Point3D(2.5, 10, 2.5), Point3D(4.5, 10, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('Front Aperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)

    new_room = room.duplicate()
    model = Model('Tiny House', [new_room])
    origin = Point3D(0, 0, 0)
    normal = Vector3D(1, 0, 0)
    model.reflect(Plane(normal, origin))

    r_cent = model.rooms[0].center.reflect(normal, origin)
    assert room.center.x == pytest.approx(r_cent.x, rel=1e-3)
    assert room.center.y == pytest.approx(r_cent.y, rel=1e-3)
    assert room.center.z == pytest.approx(r_cent.z, rel=1e-3)
    shd_cent = model.rooms[0][3].apertures[0].outdoor_shades[0].center.reflect(normal, origin)
    assert south_face.apertures[0].outdoor_shades[0].center.x == pytest.approx(shd_cent.x, rel=1e-3)
    assert south_face.apertures[0].outdoor_shades[0].center.y == pytest.approx(shd_cent.y, rel=1e-3)
    assert south_face.apertures[0].outdoor_shades[0].center.z == pytest.approx(shd_cent.z, rel=1e-3)
    a_cent = model.rooms[0][3].apertures[0].center.reflect(normal, origin)
    assert room[3].apertures[0].center.x == pytest.approx(a_cent.x, rel=1e-3)
    assert room[3].apertures[0].center.y == pytest.approx(a_cent.y, rel=1e-3)
    assert room[3].apertures[0].center.z == pytest.approx(a_cent.z, rel=1e-3)
    d_cent = model.rooms[0][1].doors[0].center.reflect(normal, origin)
    assert room[1].doors[0].center.x == pytest.approx(d_cent.x, rel=1e-3)
    assert room[1].doors[0].center.y == pytest.approx(d_cent.y, rel=1e-3)
    assert room[1].doors[0].center.z == pytest.approx(d_cent.z, rel=1e-3)


def test_check_duplicate_room_names():
    """Test the check_duplicate_room_names method."""
    room_south = Room.from_box('Zone1', 5, 5, 3, origin=Point3D(0, 0, 0))
    room_north = Room.from_box('Zone1', 5, 5, 3, origin=Point3D(0, 5, 0))
    room_south[3].apertures_by_ratio(0.4, 0.01)
    Room.solve_adjacency([room_south, room_north], 0.01)

    model_1 = Model('South House', [room_south])
    model_2 = Model('North House', [room_north])

    assert model_1.check_duplicate_room_names(False)
    model_1.add_model(model_2)
    assert not model_1.check_duplicate_room_names(False)
    with pytest.raises(ValueError):
        model_1.check_duplicate_room_names(True)


def test_check_duplicate_face_names():
    """Test the check_duplicate_face_names method."""
    pts_1 = [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(10, 10, 0), Point3D(10, 0, 0)]
    pts_2 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(0, 10, 0)]
    pts_3 = [Point3D(0, 0, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(0, 0, 3)]
    pts_4 = [Point3D(10, 10, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(10, 10, 3)]
    pts_5 = [Point3D(10, 10, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(10, 10, 3)]
    pts_6 = [Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    face_1 = Face('Face 1', Face3D(pts_1))
    face_2 = Face('Face 2', Face3D(pts_2))
    face_3 = Face('Face 3', Face3D(pts_3))
    face_4 = Face('Face 4', Face3D(pts_4))
    face_5 = Face('Face 5', Face3D(pts_5))
    face_6 = Face('Face 6', Face3D(pts_6))
    face_7 = Face('Face 1', Face3D(pts_6))
    room_1 = Room('Test Room', [face_1, face_2, face_3, face_4, face_5, face_6])
    room_2 = Room('Test Room', [face_1, face_2, face_3, face_4, face_5, face_7])

    model_1 = Model('Test House', [room_1])
    model_2 = Model('Test House', [room_2])

    assert model_1.check_duplicate_face_names(False)
    assert not model_2.check_duplicate_face_names(False)
    with pytest.raises(ValueError):
        model_2.check_duplicate_face_names(True)


def test_check_duplicate_shade_names():
    """Test the check_duplicate_shade_names method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    table_geo = Face3D.from_rectangle(2, 2, Plane(o=Point3D(1.5, 4, 1)))
    room.add_indoor_shade(Shade('Table', table_geo))

    model = Model('Test House', [room])
    assert model.check_duplicate_shade_names(False)
    tree_canopy_geo = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(5, -3, 4)))
    model.add_shade(Shade('Table', tree_canopy_geo))
    assert not model.check_duplicate_shade_names(False)
    with pytest.raises(ValueError):
        model.check_duplicate_shade_names(True)


def test_check_duplicate_sub_face_names():
    """Test the check_duplicate_sub_face_names method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    north_face = room[1]
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1),
                      Point3D(2.5, 10, 2.5), Point3D(4.5, 10, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('Front Door', Face3D(aperture_verts))

    model = Model('Test House', [room])
    assert model.check_duplicate_sub_face_names(False)
    north_face.add_aperture(aperture)
    assert not model.check_duplicate_sub_face_names(False)
    with pytest.raises(ValueError):
        model.check_duplicate_sub_face_names(True)


def test_check_missing_adjacencies():
    """Test the check_missing_adjacencies method."""
    room_south = Room.from_box('South Zone', 5, 5, 3, origin=Point3D(0, 0, 0))
    room_north = Room.from_box('North Zone', 5, 5, 3, origin=Point3D(0, 5, 0))
    room_south[1].apertures_by_ratio(0.4, 0.01)
    room_south[3].apertures_by_ratio(0.4, 0.01)
    room_north[3].apertures_by_ratio(0.4, 0.01)
    Room.solve_adjacency([room_south, room_north], 0.01)

    model_1 = Model('South House', [room_south])
    model_2 = Model('North House', [room_north])

    assert len(model_1.rooms) == 1
    assert len(model_1.faces) == 6
    assert len(model_1.apertures) == 2
    assert not model_1.check_missing_adjacencies(False)
    with pytest.raises(ValueError):
        model_1.check_missing_adjacencies(True)

    model_1.add_model(model_2)
    assert len(model_1.rooms) == 2
    assert len(model_1.faces) == 12
    assert len(model_1.apertures) == 3
    assert model_1.check_missing_adjacencies(True)


def test_check_all_air_boundaries_adjacent():
    """Test the check_all_air_boundaries_adjacent method."""
    room_south = Room.from_box('South Zone', 5, 5, 3, origin=Point3D(0, 0, 0))
    room_north = Room.from_box('North Zone', 5, 5, 3, origin=Point3D(0, 5, 0))
    room_south[3].apertures_by_ratio(0.4, 0.01)
    room_south[1].type = face_types.air_boundary
    room_north[3].type = face_types.air_boundary

    model = Model('Test House', [room_south, room_north])
    assert not model.check_all_air_boundaries_adjacent(False)
    with pytest.raises(ValueError):
        model.check_all_air_boundaries_adjacent(True)

    Room.solve_adjacency([room_south, room_north], 0.01)
    assert model.check_all_air_boundaries_adjacent(False)


def test_check_planar():
    """Test the check_planar method."""
    pts_1 = [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(10, 10, 0), Point3D(10, 0, 0)]
    pts_2 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(0, 10, 0)]
    pts_3 = [Point3D(0, 0, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(0, 0, 3)]
    pts_4 = [Point3D(10, 10, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(10, 10, 3)]
    pts_5 = [Point3D(10, 10, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(10, 10, 3)]
    pts_6 = [Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    pts_7 = [Point3D(10, 0, 3), Point3D(10, 10, 3.1), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    face_1 = Face('Face 1', Face3D(pts_1))
    face_2 = Face('Face 2', Face3D(pts_2))
    face_3 = Face('Face 3', Face3D(pts_3))
    face_4 = Face('Face 4', Face3D(pts_4))
    face_5 = Face('Face 5', Face3D(pts_5))
    face_6 = Face('Face 6', Face3D(pts_6))
    face_7 = Face('Face 7', Face3D(pts_7))
    room_1 = Room('Zone: SHOE_BOX [920980]',
                  [face_1, face_2, face_3, face_4, face_5, face_6], 0.01, 1)
    room_2 = Room('Zone: SHOE_BOX [920980]',
                  [face_1, face_2, face_3, face_4, face_5, face_7], 0.01, 1)

    model_1 = Model('South House', [room_1])
    model_2 = Model('North House', [room_2])
    assert model_1.check_planar(0.01, False)
    assert not model_2.check_planar(0.01, False)
    with pytest.raises(ValueError):
        model_2.check_planar(0.01, True)


def test_check_self_intersecting():
    """Test the check_self_intersecting method."""
    pts_1 = [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(10, 10, 0), Point3D(10, 0, 0)]
    pts_2 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(0, 10, 0)]
    pts_3 = [Point3D(0, 0, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(0, 0, 3)]
    pts_4 = [Point3D(10, 10, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(10, 10, 3)]
    pts_5 = [Point3D(10, 10, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(10, 10, 3)]
    pts_6 = [Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    pts_7 = [Point3D(10, 0, 3), Point3D(0, 10, 3), Point3D(10, 10, 3), Point3D(0, 0, 3)]
    face_1 = Face('Face 1', Face3D(pts_1))
    face_2 = Face('Face 2', Face3D(pts_2))
    face_3 = Face('Face 3', Face3D(pts_3))
    face_4 = Face('Face 4', Face3D(pts_4))
    face_5 = Face('Face 5', Face3D(pts_5))
    face_6 = Face('Face 6', Face3D(pts_6))
    face_7 = Face('Face 7', Face3D(pts_7))
    room_1 = Room('Zone: SHOE_BOX [920980]',
                  [face_1, face_2, face_3, face_4, face_5, face_6], 0.01, 1)
    room_2 = Room('Zone: SHOE_BOX [920980]',
                  [face_1, face_2, face_3, face_4, face_5, face_7], 0.01, 1)

    model_1 = Model('South House', [room_1])
    model_2 = Model('North House', [room_2])
    assert model_1.check_self_intersecting(False)
    assert not model_2.check_self_intersecting(False)
    with pytest.raises(ValueError):
        model_2.check_self_intersecting(True)


def test_check_non_zero():
    """Test the check_non_zero method."""
    pts_1 = [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(10, 10, 0), Point3D(10, 0, 0)]
    pts_2 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(0, 10, 0)]
    pts_3 = [Point3D(0, 0, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(0, 0, 3)]
    pts_4 = [Point3D(10, 10, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(10, 10, 3)]
    pts_5 = [Point3D(10, 10, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(10, 10, 3)]
    pts_6 = [Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    pts_7 = [Point3D(10, 0, 3), Point3D(10, 0.0001, 3), Point3D(0, 0.0001, 3), Point3D(0, 0, 3)]
    face_1 = Face('Face 1', Face3D(pts_1))
    face_2 = Face('Face 2', Face3D(pts_2))
    face_3 = Face('Face 3', Face3D(pts_3))
    face_4 = Face('Face 4', Face3D(pts_4))
    face_5 = Face('Face 5', Face3D(pts_5))
    face_6 = Face('Face 6', Face3D(pts_6))
    face_7 = Face('Face 7', Face3D(pts_7))
    room_1 = Room('Zone: SHOE_BOX [920980]',
                  [face_1, face_2, face_3, face_4, face_5, face_6], 0.01, 1)
    room_2 = Room('Zone: SHOE_BOX [920980]',
                  [face_1, face_2, face_3, face_4, face_5, face_6, face_7])

    model_1 = Model('South House', [room_1])
    model_2 = Model('North House', [room_2])
    assert model_1.check_non_zero(0.01, False)
    assert not model_2.check_non_zero(0.01, False)
    with pytest.raises(ValueError):
        model_2.check_non_zero(0.01, True)


def test_triangulated_apertures():
    """Test the triangulated_apertures method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    north_face = room[1]
    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1), Point3D(2.5, 10, 2.5),
                      Point3D(3.5, 10, 2.9), Point3D(4.5, 10, 2.5)]
    aperture = Aperture('Front Aperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)
    model = Model('Tiny House', [room])

    triangulated_apertures, parents_to_edit = model.triangulated_apertures()

    assert len(triangulated_apertures) == 1
    assert len(parents_to_edit) == 1
    assert len(triangulated_apertures[0]) == 3
    assert len(parents_to_edit[0]) == 3
    parents_to_edit[0][0] == aperture.name
    parents_to_edit[0][1] == north_face.name

    for ap in triangulated_apertures[0]:
        assert isinstance(ap, Aperture)
        assert len(ap.geometry) == 3


def test_triangulated_doors():
    """Test the triangulated_doors method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    north_face = room[1]
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1), Point3D(1, 10, 2.5),
                  Point3D(1.5, 10, 2.8), Point3D(2, 10, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    north_face.add_door(door)
    model = Model('Tiny House', [room])

    triangulated_doors, parents_to_edit = model.triangulated_doors()

    assert len(triangulated_doors) == 1
    assert len(parents_to_edit) == 1
    assert len(triangulated_doors[0]) == 3
    assert len(parents_to_edit[0]) == 3
    parents_to_edit[0][0] == door.name
    parents_to_edit[0][1] == north_face.name

    for dr in triangulated_doors[0]:
        assert isinstance(dr, Door)
        assert len(dr.geometry) == 3


def test_to_dict():
    """Test the Model to_dict method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    north_face = room[1]
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1),
                      Point3D(2.5, 10, 2.5), Point3D(4.5, 10, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('Front Aperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)
    model = Model('Tiny House', [room])
    model.north_angle = 15

    model_dict = model.to_dict()
    assert model_dict['type'] == 'Model'
    assert model_dict['name'] == 'TinyHouse'
    assert model_dict['display_name'] == 'Tiny House'
    assert 'rooms' in model_dict
    assert len(model_dict['rooms']) == 1
    assert 'faces' in model_dict['rooms'][0]
    assert len(model_dict['rooms'][0]['faces']) == 6
    assert 'apertures' in model_dict['rooms'][0]['faces'][3]
    assert len(model_dict['rooms'][0]['faces'][3]['apertures']) == 1
    assert 'doors' in model_dict['rooms'][0]['faces'][1]
    assert len(model_dict['rooms'][0]['faces'][1]['doors']) == 1
    assert 'outdoor_shades' in model_dict['rooms'][0]['faces'][3]['apertures'][0]
    assert len(model_dict['rooms'][0]['faces'][3]['apertures'][0]['outdoor_shades']) == 1
    assert 'north_angle' in model_dict
    assert model_dict['north_angle'] == 15
    assert 'properties' in model_dict
    assert model_dict['properties']['type'] == 'ModelProperties'


def test_to_from_dict_methods():
    """Test the to/from dict methods."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    north_face = room[1]
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1),
                      Point3D(2.5, 10, 2.5), Point3D(4.5, 10, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('Front Aperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)
    model = Model('Tiny House', [room])
    model.north_angle = 15

    model_dict = model.to_dict()
    new_model = Model.from_dict(model_dict)
    assert model_dict == new_model.to_dict()

    assert new_model.name == 'TinyHouse'
    assert new_model.display_name == 'Tiny House'
    assert new_model.north_angle == 15
    assert len(new_model.rooms) == 1
    assert isinstance(new_model.rooms[0], Room)
    assert len(new_model.faces) == 6
    assert isinstance(new_model.faces[0], Face)
    assert len(new_model.shades) == 2
    assert isinstance(new_model.shades[0], Shade)
    assert len(new_model.apertures) == 2
    assert isinstance(new_model.apertures[0], Aperture)
    assert len(new_model.doors) == 1
    assert isinstance(new_model.doors[0], Door)
    assert len(new_model.orphaned_faces) == 0
    assert len(new_model.orphaned_shades) == 0
    assert len(new_model.orphaned_apertures) == 0
    assert len(new_model.orphaned_doors) == 0


def test_writer():
    """Test the Model writer object."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    model = Model('Tiny House', [room])

    writers = [mod for mod in dir(model.to) if not mod.startswith('_')]
    for writer in writers:
        assert callable(getattr(model.to, writer))
