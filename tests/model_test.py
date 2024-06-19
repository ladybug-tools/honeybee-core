"""Test Model class."""
from honeybee.model import Model
from honeybee.room import Room
from honeybee.face import Face
from honeybee.shade import Shade
from honeybee.shademesh import ShadeMesh
from honeybee.aperture import Aperture
from honeybee.door import Door
from honeybee.boundarycondition import Surface
from honeybee.facetype import face_types
from honeybee.units import conversion_factor_to_meters

from ladybug_geometry.geometry3d import Point3D, Vector3D, Plane, Face3D, Mesh3D

import math
import pytest
import os
import json


def test_model_init():
    """Test the initialization of the Model and basic properties."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
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
    door = Door('FrontDoor', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('FrontAperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)

    model = Model('TinyHouse', [room])
    str(model)  # test the string representation of the object

    assert model.identifier == 'TinyHouse'
    assert model.display_name == 'TinyHouse'
    assert model.units == 'Meters'
    assert model.tolerance == 0.01
    assert model.angle_tolerance == 1.0
    assert len(model.rooms) == 1
    assert isinstance(model.rooms[0], Room)
    assert len(model.faces) == 6
    assert isinstance(model.faces[0], Face)
    assert len(model.apertures) == 2
    assert isinstance(model.apertures[0], Aperture)
    assert len(model.doors) == 1
    assert isinstance(model.doors[0], Door)
    assert len(model.indoor_shades) == 1
    assert isinstance(model.indoor_shades[0], Shade)
    assert len(model.outdoor_shades) == 1
    assert isinstance(model.outdoor_shades[0], Shade)
    assert len(model.orphaned_faces) == 0
    assert len(model.orphaned_shades) == 0
    assert len(model.orphaned_apertures) == 0
    assert len(model.orphaned_doors) == 0

    assert len(model.stories) == 0
    assert model.volume == pytest.approx(150, rel=1e-3)
    assert model.floor_area == pytest.approx(50, rel=1e-3)
    assert model.exposed_area == pytest.approx(140, rel=1e-3)
    assert model.exterior_wall_area == pytest.approx(90, rel=1e-3)
    assert model.exterior_roof_area == pytest.approx(50, rel=1e-3)
    assert model.exterior_aperture_area == pytest.approx(9, rel=1e-3)
    assert model.exterior_wall_aperture_area == pytest.approx(9, rel=1e-3)
    assert model.exterior_skylight_aperture_area == 0
    assert isinstance(model.min, Point3D)
    assert isinstance(model.max, Point3D)


def test_model_properties_setability():
    """Test the setting of properties on the Model."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)

    model = Model('TinyHouse', [room])

    model.display_name = 'TestBox'
    assert model.display_name == 'TestBox'
    model.units = 'Feet'
    assert model.units == 'Feet'
    model.tolerance = 0.1
    assert model.tolerance == 0.1
    model.angle_tolerance = 0.01
    assert model.angle_tolerance == 0.01
    model.tolerance = None
    assert model.tolerance == 0.01


def test_model_init_orphaned_objects():
    """Test the initialization of the Model with orphaned objects."""
    pts_1 = [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(10, 10, 0), Point3D(10, 0, 0)]
    pts_2 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(0, 10, 0)]
    pts_3 = [Point3D(0, 0, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(0, 0, 3)]
    pts_4 = [Point3D(10, 10, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(10, 10, 3)]
    pts_5 = [Point3D(10, 10, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(10, 10, 3)]
    pts_6 = [Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    face_1 = Face('Face1', Face3D(pts_1))
    face_2 = Face('Face2', Face3D(pts_2))
    face_3 = Face('Face3', Face3D(pts_3))
    face_4 = Face('Face4', Face3D(pts_4))
    face_5 = Face('Face5', Face3D(pts_5))
    face_6 = Face('Face6', Face3D(pts_6))
    face_2.apertures_by_ratio(0.4, 0.01)
    face_2.apertures[0].overhang(0.5, indoor=False)
    face_2.apertures[0].overhang(0.5, indoor=True)
    face_2.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    aperture_verts = [Point3D(4.5, 5, 1), Point3D(2.5, 5, 1),
                      Point3D(2.5, 5, 2.5), Point3D(4.5, 5, 2.5)]
    door = Door('FrontDoor', Face3D(door_verts))
    aperture = Aperture('Partition', Face3D(aperture_verts))
    table_geo = Face3D.from_rectangle(2, 2, Plane(o=Point3D(1.5, 4, 1)))
    table = Shade('Table', table_geo)
    tree_canopy_geo = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(5, -3, 4)))
    tree_canopy = Shade('TreeCanopy', tree_canopy_geo)

    pts = (Point3D(0, 0, 4), Point3D(0, 2, 4), Point3D(2, 2, 4),
           Point3D(2, 0, 4), Point3D(4, 0, 4))
    mesh = Mesh3D(pts, [(0, 1, 2, 3), (2, 3, 4)])
    awning = ShadeMesh('Awning', mesh)

    model = Model('TinyHouse', [], [face_1, face_2, face_3, face_4, face_5, face_6],
                  [table, tree_canopy], [aperture], [door], [awning])

    assert len(model.rooms) == 0
    assert len(model.faces) == 6
    assert isinstance(model.faces[0], Face)
    assert len(model.shades) == 4
    assert isinstance(model.shades[0], Shade)
    assert len(model.apertures) == 2
    assert isinstance(model.apertures[0], Aperture)
    assert len(model.doors) == 1
    assert isinstance(model.doors[0], Door)
    assert len(model.shade_meshes) == 1
    assert isinstance(model.shade_meshes[0], ShadeMesh)
    assert len(model.orphaned_faces) == 6
    assert len(model.orphaned_shades) == 2
    assert len(model.orphaned_apertures) == 1
    assert len(model.orphaned_doors) == 1


def test_adjacent_zone_model():
    """Test the solve adjacency method with an interior aperture."""
    room_south = Room.from_box('SouthZone', 5, 5, 3, origin=Point3D(0, 0, 0))
    room_north = Room.from_box('NorthZone', 5, 5, 3, origin=Point3D(0, 5, 0))
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
    door = Door('FrontDoor', Face3D(door_verts))
    room_north[1].add_door(door)
    aperture = Aperture('FrontAperture', Face3D(aperture_verts))
    room_north[1].add_aperture(aperture)
    Room.solve_adjacency([room_south, room_north], 0.01)

    model = Model('TwoRoomHouse', [room_south, room_north])

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
        new_model.rooms[1][3].apertures[0].identifier
    assert new_model.rooms[1][3].apertures[0].boundary_condition.boundary_condition_object == \
        new_model.rooms[0][1].apertures[0].identifier


def test_model_init_from_objects():
    """Test the initialization of the Model from_objects."""
    pts_1 = [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(10, 10, 0), Point3D(10, 0, 0)]
    pts_2 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(0, 10, 0)]
    pts_3 = [Point3D(0, 0, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(0, 0, 3)]
    pts_4 = [Point3D(10, 10, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(10, 10, 3)]
    pts_5 = [Point3D(10, 10, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(10, 10, 3)]
    pts_6 = [Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    face_1 = Face('Face1', Face3D(pts_1))
    face_2 = Face('Face2', Face3D(pts_2))
    face_3 = Face('Face3', Face3D(pts_3))
    face_4 = Face('Face4', Face3D(pts_4))
    face_5 = Face('Face5', Face3D(pts_5))
    face_6 = Face('Face6', Face3D(pts_6))
    face_2.apertures_by_ratio(0.4, 0.01)
    face_2.apertures[0].overhang(0.5, indoor=False)
    face_2.apertures[0].overhang(0.5, indoor=True)
    face_2.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    aperture_verts = [Point3D(4.5, 5, 1), Point3D(2.5, 5, 1),
                      Point3D(2.5, 5, 2.5), Point3D(4.5, 5, 2.5)]
    door = Door('FrontDoor', Face3D(door_verts))
    aperture = Aperture('Partition', Face3D(aperture_verts))
    table_geo = Face3D.from_rectangle(2, 2, Plane(o=Point3D(1.5, 4, 1)))
    table = Shade('Table', table_geo)
    tree_canopy_geo = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(5, -3, 4)))
    tree_canopy = Shade('TreeCanopy', tree_canopy_geo)
    pts = (Point3D(0, 0, 4), Point3D(0, 2, 4), Point3D(2, 2, 4),
           Point3D(2, 0, 4), Point3D(4, 0, 4))
    mesh = Mesh3D(pts, [(0, 1, 2, 3), (2, 3, 4)])
    awning = ShadeMesh('Awning', mesh)

    model = Model.from_objects(
        'TinyHouse', [face_1, face_2, face_3, face_4, face_5, face_6,
                      table, tree_canopy, aperture, door, awning])

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

    model.remove_shades()
    assert len(model.shades) == 2
    model.remove_all_shades()
    assert len(model.shades) == 0
    model.remove_apertures()
    assert len(model.apertures) == 1
    model.remove_all_apertures()
    assert len(model.apertures) == 0
    model.remove_doors()
    assert len(model.doors) == 0
    model.remove_faces()
    assert len(model.faces) == 0


def test_rooms_by_identifier():
    """Test the rooms_by_identifier method."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
    model = Model('TinyHouse', [room])

    assert len(model.rooms_by_identifier(['TinyHouseZone'])) == 1
    with pytest.raises(ValueError):
        model.rooms_by_identifier(['NotARoom'])

    model.remove_rooms()
    with pytest.raises(ValueError):
        model.shades_by_identifier(['TinyHouseZone'])


def test_faces_by_identifier():
    """Test the faces_by_identifier method."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
    model = Model('TinyHouse', [room])

    assert len(
        model.faces_by_identifier(['TinyHouseZone_Front', 'TinyHouseZone_Back'])) == 2
    with pytest.raises(ValueError):
        model.faces_by_identifier(['NotAFace'])


def test_shades_by_identifier():
    """Test the shades_by_identifier method."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    model = Model('TinyHouse', [room])

    assert len(model.shades_by_identifier(['TinyHouseZone_Back_Glz0_OutOverhang0'])) == 1
    with pytest.raises(ValueError):
        model.shades_by_identifier(['NotAShade'])

    model.remove_assigned_shades()
    with pytest.raises(ValueError):
        model.shades_by_identifier(['TinyHouseZone_Back_Glz0_OutOverhang0'])


def test_apertures_by_identifier():
    """Test the apertures_by_identifier method."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    model = Model('TinyHouse', [room])

    assert len(model.apertures_by_identifier(['TinyHouseZone_Back_Glz0'])) == 1
    with pytest.raises(ValueError):
        model.apertures_by_identifier(['NotAnAperture'])

    model.remove_assigned_apertures()
    with pytest.raises(ValueError):
        model.shades_by_identifier(['TinyHouseZone_Back_Glz0'])


def test_doors_by_identifier():
    """Test the doors_by_identifier method."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
    north_face = room[1]
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    door = Door('FrontDoor', Face3D(door_verts))
    north_face.add_door(door)
    model = Model('TinyHouse', [room])

    assert len(model.doors_by_identifier(['FrontDoor'])) == 1
    with pytest.raises(ValueError):
        model.doors_by_identifier(['NotADoor'])

    model.remove_assigned_doors()
    with pytest.raises(ValueError):
        model.shades_by_identifier(['FrontDoor'])


def test_shade_meshes_by_identifier():
    """Test the shade_meshes_by_identifier method."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
    pts = (Point3D(0, 0, 4), Point3D(0, 2, 4), Point3D(2, 2, 4),
           Point3D(2, 0, 4), Point3D(4, 0, 4))
    mesh = Mesh3D(pts, [(0, 1, 2, 3), (2, 3, 4)])
    awning = ShadeMesh('Awning_1', mesh)
    model = Model('TinyHouse', [room], shade_meshes=[awning])

    assert len(model.shade_meshes_by_identifier(['Awning_1'])) == 1
    with pytest.raises(ValueError):
        model.shade_meshes_by_identifier(['NotAShadeMesh'])

    model.remove_shade_meshes()
    with pytest.raises(ValueError):
        model.shade_meshes_by_identifier(['Awning_1'])


def test_model_add_prefix():
    """Test the model add_prefix method."""
    room = Room.from_box('ShoeBoxZone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.5, 0.01)
    table_geo = Face3D.from_rectangle(2, 2, Plane(o=Point3D(1.5, 4, 1)))
    room.add_indoor_shade(Shade('Table', table_geo))
    prefix = 'New'
    model = Model('ShoeBox', [room])
    model.add_prefix(prefix)

    assert room.identifier.startswith(prefix)
    for face in room.faces:
        assert face.identifier.startswith(prefix)
        for ap in face.apertures:
            assert ap.identifier.startswith(prefix)
    for shd in room.shades:
        assert shd.identifier.startswith(prefix)


def test_reset_room_ids():
    """Test the reset_room_ids method."""
    model_json = './tests/json/model_with_adiabatic.hbjson'
    parsed_model = Model.from_hbjson(model_json)

    new_model = parsed_model.duplicate()
    new_model.reset_room_ids()

    assert new_model.rooms[0].identifier != parsed_model.rooms[0].identifier


def test_reset_ids():
    """Test the reset_ids method."""
    model_json = './tests/json/model_with_adiabatic.hbjson'
    parsed_model = Model.from_hbjson(model_json)

    new_model = parsed_model.duplicate()
    new_model.reset_ids(True)

    assert new_model.rooms[0].identifier != parsed_model.rooms[0].identifier
    assert new_model.check_missing_adjacencies() == ''


def test_offset_aperture_edges():
    """Test the Face offset_aperture_edges method."""
    model_json = './tests/json/room_for_window_offset.hbjson'
    parsed_model = Model.from_hbjson(model_json)
    test_room = parsed_model.rooms[0]
    test_face = test_room[1]

    orig_area = test_face.aperture_area
    test_face.offset_aperture_edges(-0.3, 0.01)
    new_area = test_face.aperture_area
    assert new_area < orig_area
    assert len(test_face.apertures) == 3

    test_face.offset_aperture_edges(0.6, 0.01)
    new_area = test_face.aperture_area
    assert new_area > orig_area
    assert len(test_face.apertures) == 3

    test_face.fix_invalid_sub_faces(True, True)
    fix_area = test_face.aperture_area
    assert len(test_face.apertures) == 1
    assert fix_area < new_area


def test_move():
    """Test the Model move method."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
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
    door = Door('FrontDoor', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('FrontAperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)

    new_room = room.duplicate()
    model = Model('TinyHouse', [new_room])

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
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
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
    door = Door('FrontDoor', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('FrontAperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)

    new_room = room.duplicate()
    model = Model('TinyHouse', [new_room])
    model.scale(0.5)

    assert room.floor_area == model.rooms[0].floor_area * 2 ** 2
    assert room.volume == model.rooms[0].volume * 2 ** 3
    assert south_face.apertures[0].indoor_shades[0].area == \
        model.rooms[0][3].apertures[0].indoor_shades[0].area * 2 ** 2
    assert south_face.apertures[0].outdoor_shades[0].area == \
        model.rooms[0][3].apertures[0].outdoor_shades[0].area * 2 ** 2
    assert room[3].apertures[0].area == model.rooms[0][3].apertures[0].area * 2 ** 2
    assert room[1].doors[0].area == model.rooms[0][1].doors[0].area * 2 ** 2


def test_generate_exterior_face_grid():
    """Test the generate_exterior_face_grid method."""
    room = Room.from_box('ShoeBoxZone', 5, 10, 3)
    model = Model('TinyHouse', [room])
    mesh_grid = model.generate_exterior_face_grid(1, face_type='Wall')
    assert len(mesh_grid.faces) == 60 + 30
    mesh_grid = model.generate_exterior_face_grid(0.5, face_type='All')
    assert len(mesh_grid.faces) == 200 + 240 + 120


def test_generate_exterior_aperture_grid():
    """Test the generate_exterior_aperture_grid method."""
    room = Room.from_box('ShoeBoxZone', 5, 10, 3)
    room[3].apertures_by_ratio(0.4)
    model = Model('TinyHouse', [room])
    mesh_grid = model.generate_exterior_aperture_grid(1)
    assert len(mesh_grid.faces) != 0


def test_apertures_by_ratio():
    """Test the apertures_by_ratio methods."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
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
    door = Door('FrontDoor', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('FrontAperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)

    model = Model('TinyHouse', [room])

    assert model.exterior_aperture_area / model.exterior_wall_area == \
        pytest.approx(0.1, rel=1e-3)
    model.wall_apertures_by_ratio(0.4)
    assert model.exterior_aperture_area / model.exterior_wall_area == \
        pytest.approx(0.4, rel=1e-3)

    assert model.exterior_skylight_aperture_area / model.exterior_roof_area == 0
    model.skylight_apertures_by_ratio(0.05)
    assert model.exterior_skylight_aperture_area / model.exterior_roof_area == \
        pytest.approx(0.05, rel=1e-3)


def test_convert_to_units():
    """Test the Model convert_to_units method."""
    room = Room.from_box('TinyHouseZone', 120, 240, 96)
    inches_conversion = conversion_factor_to_meters('Inches')

    model = Model('TinyHouse', [room], units='Inches')
    model.convert_to_units('Meters')

    assert room.floor_area == pytest.approx(120 * 240 * (inches_conversion ** 2), rel=1e-3)
    assert room.volume == pytest.approx(120 * 240 * 96 * (inches_conversion ** 3), rel=1e-3)
    assert model.units == 'Meters'


def test_assign_stories_by_floor_height():
    """Test the Model assign_stories_by_floor_height method."""
    first_floor = Room.from_box('First_Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second_Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    for face in first_floor[1:5]:
        face.apertures_by_ratio(0.2, 0.01)
    for face in second_floor[1:5]:
        face.apertures_by_ratio(0.2, 0.01)
    pts_1 = [Point3D(0, 0, 6), Point3D(0, 10, 6), Point3D(10, 10, 6), Point3D(10, 0, 6)]
    pts_2 = [Point3D(0, 0, 6), Point3D(5, 0, 9), Point3D(5, 10, 9), Point3D(0, 10, 6)]
    pts_3 = [Point3D(10, 0, 6), Point3D(10, 10, 6), Point3D(5, 10, 9), Point3D(5, 0, 9)]
    pts_4 = [Point3D(0, 0, 6), Point3D(10, 0, 6), Point3D(5, 0, 9)]
    pts_5 = [Point3D(10, 10, 6), Point3D(0, 10, 6), Point3D(5, 10, 9)]
    face_1 = Face('AtticFace1', Face3D(pts_1))
    face_2 = Face('AtticFace2', Face3D(pts_2))
    face_3 = Face('AtticFace3', Face3D(pts_3))
    face_4 = Face('AtticFace4', Face3D(pts_4))
    face_5 = Face('AtticFace5', Face3D(pts_5))
    attic = Room('Attic', [face_1, face_2, face_3, face_4, face_5], 0.01, 1)
    Room.solve_adjacency([first_floor, second_floor, attic], 0.01)
    model = Model('MultiZoneSingleFamilyHouse', [first_floor, second_floor, attic])

    assert len(model.stories) == 0
    model.assign_stories_by_floor_height(2.0)
    assert len(model.stories) == 3
    assert first_floor.story == 'Floor1'
    assert second_floor.story == 'Floor2'
    assert attic.story == 'Floor3'
    model.assign_stories_by_floor_height(4.0, overwrite=True)
    assert len(model.stories) == 2
    assert first_floor.story == second_floor.story == 'Floor1'
    assert attic.story == 'Floor2'


def test_rotate():
    """Test the Model rotate method."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
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
    door = Door('FrontDoor', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('FrontAperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)

    new_room = room.duplicate()
    model = Model('TinyHouse', [new_room])
    origin = Point3D(0, 0, 0)
    axis = Vector3D(1, 0, 0)
    model.rotate(axis, 90, origin)

    r_cent = model.rooms[0].center.rotate(axis, math.radians(-90), origin)
    assert room.center.x == pytest.approx(r_cent.x, rel=1e-3)
    assert room.center.y == pytest.approx(r_cent.y, rel=1e-3)
    assert room.center.z == pytest.approx(r_cent.z, rel=1e-3)
    shd_cent = model.rooms[0][3].apertures[0].outdoor_shades[0].center.rotate(
        axis, math.radians(-90), origin)
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
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
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
    door = Door('FrontDoor', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('FrontAperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)

    new_room = room.duplicate()
    model = Model('TinyHouse', [new_room])
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
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
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
    door = Door('FrontDoor', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('FrontAperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)

    new_room = room.duplicate()
    model = Model('TinyHouse', [new_room])
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


def test_simplify_apertures():
    """Test the rectangularize_apertures method."""
    model_json = './tests/json/minor_geometry/existing_model.hbjson'
    parsed_model = Model.from_hbjson(model_json)
    assert isinstance(parsed_model, Model)
    start_ratio = parsed_model.exterior_aperture_area

    parsed_model.simplify_apertures()

    parsed_model.check_sub_faces_valid()
    end_area = parsed_model.exterior_aperture_area
    assert start_ratio == pytest.approx(end_area, rel=1e-3)


def test_rectangularize_apertures():
    """Test the rectangularize_apertures method."""
    model_json = './tests/json/minor_geometry/existing_model.hbjson'
    parsed_model = Model.from_hbjson(model_json)
    assert isinstance(parsed_model, Model)

    parsed_model.rectangularize_apertures(0.65)
    parsed_model.check_sub_faces_valid()


def test_check_duplicate_room_identifiers():
    """Test the check_duplicate_room_identifiers method."""
    room_south = Room.from_box('Zone1', 5, 5, 3, origin=Point3D(0, 0, 0))
    room_north = Room.from_box('Zone1', 5, 5, 3, origin=Point3D(0, 5, 0))
    room_south[3].apertures_by_ratio(0.4, 0.01)
    Room.solve_adjacency([room_south, room_north], 0.01)

    model_1 = Model('SouthHouse', [room_south])
    model_2 = Model('NorthHouse', [room_north])

    assert model_1.check_duplicate_room_identifiers(False) == ''
    model_1.add_model(model_2)
    assert model_1.check_duplicate_room_identifiers(False) != ''
    with pytest.raises(ValueError):
        model_1.check_duplicate_room_identifiers(True)


def test_check_duplicate_face_identifiers():
    """Test the check_duplicate_face_identifiers method."""
    pts_1 = [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(10, 10, 0), Point3D(10, 0, 0)]
    pts_2 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(0, 10, 0)]
    pts_3 = [Point3D(0, 0, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(0, 0, 3)]
    pts_4 = [Point3D(10, 10, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(10, 10, 3)]
    pts_5 = [Point3D(10, 10, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(10, 10, 3)]
    pts_6 = [Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    face_1 = Face('Face1', Face3D(pts_1))
    face_2 = Face('Face2', Face3D(pts_2))
    face_3 = Face('Face3', Face3D(pts_3))
    face_4 = Face('Face4', Face3D(pts_4))
    face_5 = Face('Face5', Face3D(pts_5))
    face_6 = Face('Face6', Face3D(pts_6))
    face_7 = Face('Face1', Face3D(pts_6))
    room_1 = Room('TestRoom', [face_1, face_2, face_3, face_4, face_5, face_6])
    room_2 = Room('TestRoom', [face_1, face_2, face_3, face_4, face_5, face_7])

    model_1 = Model('TestHouse', [room_1])
    model_2 = Model('TestHouse', [room_2])

    assert model_1.check_duplicate_face_identifiers(False) == ''
    assert model_2.check_duplicate_face_identifiers(False) != ''
    with pytest.raises(ValueError):
        model_2.check_duplicate_face_identifiers(True)


def test_check_duplicate_shade_identifiers():
    """Test the check_duplicate_shade_identifiers method."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    table_geo = Face3D.from_rectangle(2, 2, Plane(o=Point3D(1.5, 4, 1)))
    room.add_indoor_shade(Shade('Table', table_geo))

    model = Model('TestHouse', [room])
    assert model.check_duplicate_shade_identifiers(False) == ''
    tree_canopy_geo = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(5, -3, 4)))
    model.add_shade(Shade('Table', tree_canopy_geo))
    assert model.check_duplicate_shade_identifiers(False) != ''
    with pytest.raises(ValueError):
        model.check_duplicate_shade_identifiers(True)


def test_check_duplicate_sub_face_identifiers():
    """Test the check_duplicate_sub_face_identifiers method."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
    north_face = room[1]
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1),
                      Point3D(2.5, 10, 2.5), Point3D(4.5, 10, 2.5)]
    door = Door('FrontDoor', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('FrontDoor', Face3D(aperture_verts))

    model = Model('TestHouse', [room])
    assert model.check_duplicate_sub_face_identifiers(False) == ''
    north_face.add_aperture(aperture)
    assert model.check_duplicate_sub_face_identifiers(False) != ''
    with pytest.raises(ValueError):
        model.check_duplicate_sub_face_identifiers(True)


def test_check_duplicate_shade_mesh_identifiers():
    """Test the check_duplicate_shade_mesh_identifiers method."""
    pts = (Point3D(0, 0, 4), Point3D(0, 2, 4), Point3D(2, 2, 4),
           Point3D(2, 0, 4), Point3D(4, 0, 4))
    mesh = Mesh3D(pts, [(0, 1, 2, 3), (2, 3, 4)])
    awning_1 = ShadeMesh('Awning_1', mesh)

    model = Model('TestHouse', shade_meshes=[awning_1])
    assert model.check_duplicate_shade_mesh_identifiers(False) == ''
    pts2 = (Point3D(0, 0, 2), Point3D(0, 2, 2), Point3D(2, 2, 2))
    mesh2 = Mesh3D(pts2, [(0, 1, 2)])
    model.add_shade_mesh(ShadeMesh('Awning_1', mesh2))
    assert model.check_duplicate_shade_mesh_identifiers(False) != ''
    with pytest.raises(ValueError):
        model.check_duplicate_shade_mesh_identifiers(True)


def test_check_missing_adjacencies():
    """Test the check_missing_adjacencies method."""
    room_south = Room.from_box('SouthZone', 5, 5, 3, origin=Point3D(0, 0, 0))
    room_north = Room.from_box('NorthZone', 5, 5, 3, origin=Point3D(0, 5, 0))
    room_south[1].apertures_by_ratio(0.4, 0.01)
    room_south[3].apertures_by_ratio(0.4, 0.01)
    room_north[3].apertures_by_ratio(0.4, 0.01)
    Room.solve_adjacency([room_south, room_north], 0.01)

    model_1 = Model('SouthHouse', [room_south])
    model_2 = Model('NorthHouse', [room_north])

    assert len(model_1.rooms) == 1
    assert len(model_1.faces) == 6
    assert len(model_1.apertures) == 2
    with pytest.raises(ValueError):
        model_1.check_missing_adjacencies()
    assert model_1.check_missing_adjacencies(False) != ''

    model_1.add_model(model_2)
    assert len(model_1.rooms) == 2
    assert len(model_1.faces) == 12
    assert len(model_1.apertures) == 3
    assert model_1.check_missing_adjacencies() == ''


def test_check_all_air_boundaries_adjacent():
    """Test the check_all_air_boundaries_adjacent method."""
    room_south = Room.from_box('SouthZone', 5, 5, 3, origin=Point3D(0, 0, 0))
    room_north = Room.from_box('NorthZone', 5, 5, 3, origin=Point3D(0, 5, 0))
    room_south[3].apertures_by_ratio(0.4, 0.01)
    room_south[1].type = face_types.air_boundary
    room_north[3].type = face_types.air_boundary

    model = Model('TestHouse', [room_south, room_north])
    assert model.check_all_air_boundaries_adjacent(False) != ''
    with pytest.raises(ValueError):
        model.check_all_air_boundaries_adjacent(True)

    Room.solve_adjacency([room_south, room_north], 0.01)
    assert model.check_all_air_boundaries_adjacent(False) == ''


def test_check_planar():
    """Test the check_planar method."""
    pts_1 = [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(10, 10, 0), Point3D(10, 0, 0)]
    pts_2 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(0, 10, 0)]
    pts_3 = [Point3D(0, 0, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(0, 0, 3)]
    pts_4 = [Point3D(10, 10, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(10, 10, 3)]
    pts_5 = [Point3D(10, 10, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(10, 10, 3)]
    pts_6 = [Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    pts_7 = [Point3D(10, 0, 3), Point3D(10, 10, 3.1), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    face_1 = Face('Face1', Face3D(pts_1))
    face_2 = Face('Face2', Face3D(pts_2))
    face_3 = Face('Face3', Face3D(pts_3))
    face_4 = Face('Face4', Face3D(pts_4))
    face_5 = Face('Face5', Face3D(pts_5))
    face_6 = Face('Face6', Face3D(pts_6))
    face_7 = Face('Face7', Face3D(pts_7))
    room_1 = Room('ZoneSHOE_BOX920980',
                  [face_1, face_2, face_3, face_4, face_5, face_6], 0.01, 1)
    room_2 = Room('ZoneSHOE_BOX920980',
                  [face_1, face_2, face_3, face_4, face_5, face_7], 0.01, 1)

    model_1 = Model('SouthHouse', [room_1])
    model_2 = Model('NorthHouse', [room_2])
    assert model_1.check_planar(0.01, False) == ''
    assert model_2.check_planar(0.01, False) != ''
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
    pts_7 = [Point3D(10, 0, 3), Point3D(0, 5, 3), Point3D(10, 10, 3), Point3D(0, 0, 3)]
    pts_8 = [Point3D(0, 5, 3), Point3D(10, 10, 3), Point3D(10, 0, 3)]
    face_1 = Face('Face1', Face3D(pts_1))
    face_2 = Face('Face2', Face3D(pts_2))
    face_3 = Face('Face3', Face3D(pts_3))
    face_4 = Face('Face4', Face3D(pts_4))
    face_5 = Face('Face5', Face3D(pts_5))
    face_6 = Face('Face6', Face3D(pts_6))
    face_7 = Face('Face7', Face3D(pts_7))
    face_8 = Face('Face8', Face3D(pts_8))
    room_1 = Room('ZoneSHOE_BOX920980',
                  [face_1, face_2, face_3, face_4, face_5, face_6], 0.01, 1)
    room_2 = Room('ZoneSHOE_BOX920980',
                  [face_1, face_2, face_3, face_4, face_5, face_7, face_8], 0.01, 1)

    model_1 = Model('SouthHouse', [room_1])
    model_2 = Model('NorthHouse', [room_2])
    assert model_1.check_self_intersecting(0.01, False) == ''
    assert model_2.check_self_intersecting(0.01, False) != ''
    with pytest.raises(ValueError):
        model_2.check_self_intersecting(0.01, True)


def test_triangulated_apertures():
    """Test the triangulated_apertures method."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
    north_face = room[1]
    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1), Point3D(2.5, 10, 2.5),
                      Point3D(3.5, 10, 2.9), Point3D(4.5, 10, 2.5)]
    aperture = Aperture('FrontAperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)
    model = Model('TinyHouse', [room])

    triangulated_apertures, parents_to_edit = model.triangulated_apertures()

    assert len(triangulated_apertures) == 1
    assert len(parents_to_edit) == 1
    assert len(triangulated_apertures[0]) == 3
    assert len(parents_to_edit[0]) == 3
    parents_to_edit[0][0] == aperture.identifier
    parents_to_edit[0][1] == north_face.identifier

    for ap in triangulated_apertures[0]:
        assert isinstance(ap, Aperture)
        assert len(ap.geometry) == 3


def test_triangulated_doors():
    """Test the triangulated_doors method."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
    north_face = room[1]
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1), Point3D(1, 10, 2.5),
                  Point3D(1.5, 10, 2.8), Point3D(2, 10, 2.5)]
    door = Door('FrontDoor', Face3D(door_verts))
    north_face.add_door(door)
    model = Model('TinyHouse', [room])

    triangulated_doors, parents_to_edit = model.triangulated_doors()

    assert len(triangulated_doors) == 1
    assert len(parents_to_edit) == 1
    assert len(triangulated_doors[0]) == 3
    assert len(parents_to_edit[0]) == 3
    parents_to_edit[0][0] == door.identifier
    parents_to_edit[0][1] == north_face.identifier

    for dr in triangulated_doors[0]:
        assert isinstance(dr, Door)
        assert len(dr.geometry) == 3


def test_to_dict():
    """Test the Model to_dict method."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
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
    door = Door('FrontDoor', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('FrontAperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)
    pts = (Point3D(0, 0, 4), Point3D(0, 2, 4), Point3D(2, 2, 4),
           Point3D(2, 0, 4), Point3D(4, 0, 4))
    mesh = Mesh3D(pts, [(0, 1, 2, 3), (2, 3, 4)])
    awning_1 = ShadeMesh('Awning_1', mesh)

    model = Model('TinyHouse', [room], shade_meshes=[awning_1])

    model_dict = model.to_dict()
    assert model_dict['type'] == 'Model'
    assert model_dict['identifier'] == 'TinyHouse'
    assert model_dict['display_name'] == 'TinyHouse'
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
    assert 'shade_meshes' in model_dict
    assert len(model_dict['shade_meshes']) == 1
    assert 'properties' in model_dict
    assert model_dict['properties']['type'] == 'ModelProperties'


def test_to_from_dict_methods():
    """Test the to/from dict methods."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
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
    door = Door('FrontDoor', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('FrontAperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)
    pts = (Point3D(0, 0, 4), Point3D(0, 2, 4), Point3D(2, 2, 4),
           Point3D(2, 0, 4), Point3D(4, 0, 4))
    mesh = Mesh3D(pts, [(0, 1, 2, 3), (2, 3, 4)])
    awning_1 = ShadeMesh('Awning_1', mesh)

    model = Model('TinyHouse', [room], shade_meshes=[awning_1])

    model_dict = model.to_dict()
    new_model = Model.from_dict(model_dict)
    assert model_dict == new_model.to_dict()

    assert new_model.identifier == 'TinyHouse'
    assert new_model.display_name == 'TinyHouse'
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
    assert len(new_model.shade_meshes) == 1
    assert isinstance(new_model.shade_meshes[0], ShadeMesh)
    assert len(new_model.orphaned_faces) == 0
    assert len(new_model.orphaned_shades) == 0
    assert len(new_model.orphaned_apertures) == 0
    assert len(new_model.orphaned_doors) == 0


def test_from_dict_method_extensions():
    """Test from_dict method with a bunch of un-serialize-able extension properties."""
    model_json = './tests/json/model_with_adiabatic.hbjson'
    with open(model_json) as json_file:
        data = json.load(json_file)
    parsed_model = Model.from_dict(data)

    assert isinstance(parsed_model, Model)


def test_comparison_report():
    """Test the comparison_report method."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
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
    door = Door('FrontDoor', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('FrontAperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)
    model = Model('TinyHouse', [room])

    new_model = model.duplicate()
    comp_report = model.comparison_report(new_model)
    assert len(comp_report['changed_objects']) == 0
    assert len(comp_report['added_objects']) == 0
    assert len(comp_report['deleted_objects']) == 0

    new_model.convert_to_units('Feet')
    comp_report = model.comparison_report(new_model)
    assert len(comp_report['changed_objects']) == 0
    assert len(comp_report['added_objects']) == 0
    assert len(comp_report['deleted_objects']) == 0

    north_face.remove_apertures()
    comp_report = model.comparison_report(new_model)
    assert len(comp_report['changed_objects']) == 1
    assert comp_report['changed_objects'][0]['geometry_changed']
    assert len(comp_report['added_objects']) == 0
    assert len(comp_report['deleted_objects']) == 0


def test_from_hbjson():
    """Test from_hbjson."""
    model_json = './tests/json/model_with_adiabatic.hbjson'
    parsed_model = Model.from_hbjson(model_json)
    assert isinstance(parsed_model, Model)


def test_to_hbjson():
    """Test the Model to_hbjson method."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
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
    door = Door('FrontDoor', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('FrontAperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)
    model = Model('TinyHouse', [room])

    path = './tests/json'
    model_hbjson = model.to_hbjson("test", path)
    assert os.path.isfile(model_hbjson)
    with open(model_hbjson) as f:
        model_dict = json.load(f)
    assert model_dict['type'] == 'Model'
    assert model_dict['identifier'] == 'TinyHouse'
    assert model_dict['display_name'] == 'TinyHouse'
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
    assert 'properties' in model_dict
    assert model_dict['properties']['type'] == 'ModelProperties'

    new_model = Model.from_hbjson(model_hbjson)
    assert isinstance(new_model, Model)
    os.remove(model_hbjson)


def test_to_hbpkl():
    """Test the Model to_hbpkl method."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
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
    door = Door('FrontDoor', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('FrontAperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)
    model = Model('TinyHouse', [room])

    path = './tests/json'
    model_hbpkl = model.to_hbpkl('test', path)
    assert os.path.isfile(model_hbpkl)
    new_model = Model.from_hbpkl(model_hbpkl)
    assert isinstance(new_model, Model)
    os.remove(model_hbpkl)


def test_to_stl():
    """Test the Model to_stl method."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
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
    door = Door('FrontDoor', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('FrontAperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)
    model = Model('TinyHouse', [room])

    path = './tests/stl'
    model_stl = model.to_stl('test', path)
    assert os.path.isfile(model_stl)
    new_model = Model.from_stl(model_stl)
    assert isinstance(new_model, Model)
    os.remove(model_stl)


def test_from_stl():
    """Test the Model from_stl method."""
    file_path = 'tests/stl/cube_binary.stl'
    model = Model.from_stl(file_path, geometry_to_faces=True)
    assert len(model.faces) == 12
    assert all((len(f.geometry) == 3 for f in model.faces))

    file_path = 'tests/stl/cube_ascii.stl'
    model = Model.from_stl(file_path, geometry_to_faces=False)
    assert len(model.shade_meshes) == 1
    assert len(model.shade_meshes[0].faces) == 12
    assert all((len(f) == 3 for f in model.shade_meshes[0].faces))


def test_writer():
    """Test the Model writer object."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
    model = Model('TinyHouse', [room])

    writers = [mod for mod in dir(model.to) if not mod.startswith('_')]
    for writer in writers:
        assert callable(getattr(model.to, writer))
