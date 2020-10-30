"""Test Room class."""
from honeybee.face import Face
from honeybee.aperture import Aperture
from honeybee.shade import Shade
from honeybee.room import Room
from honeybee.boundarycondition import boundary_conditions, Surface, Outdoors, Ground

from ladybug_geometry.geometry2d.pointvector import Vector2D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.plane import Plane
from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.geometry3d.polyface import Polyface3D

import pytest


def test_init():
    """Test the initialization of a room and basic properties."""
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
    room = Room('ZoneSHOE_BOX920980',
                [face_1, face_2, face_3, face_4, face_5, face_6], 0.01, 1)

    str(room)  # test the string representation of the room
    assert room.identifier == 'ZoneSHOE_BOX920980'
    assert room.display_name == 'ZoneSHOE_BOX920980'
    assert room.multiplier == 1
    assert room.story is None
    assert isinstance(room.geometry, Polyface3D)
    assert len(room.geometry.vertices) == 8
    assert len(room) == 6
    assert room.center == Point3D(5, 5, 1.5)
    assert room.volume == 300
    assert room.floor_area == 100
    assert room.exposed_area == 220
    assert room.exterior_wall_area == 120
    assert room.exterior_aperture_area == 0
    assert room.average_floor_height == 0
    assert not room.has_parent
    assert room.check_solid(0.01, 1)

    assert room[0].normal == Vector3D(0, 0, -1)
    assert room[1].normal == Vector3D(-1, 0, 0)
    assert room[2].normal == Vector3D(0, -1, 0)
    assert room[3].normal == Vector3D(0, 1, 0)
    assert room[4].normal == Vector3D(1, 0, 0)
    assert room[5].normal == Vector3D(0, 0, 1)


def test_init_open():
    """Test the initialization of a room with open geometry."""
    pts_1 = [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(10, 10, 0), Point3D(10, 0, 0)]
    pts_2 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(0, 10, 0)]
    pts_3 = [Point3D(0, 0, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(0, 0, 3)]
    pts_4 = [Point3D(10, 10, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(10, 10, 3)]
    pts_5 = [Point3D(10, 10, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(10, 10, 3)]
    pts_6 = [Point3D(10, 0, 3), Point3D(10, 2.5, 3), Point3D(0, 2.5, 3), Point3D(0, 0, 3)]
    pts_7 = [Point3D(10, 2.5, 3), Point3D(10, 5, 3), Point3D(0, 5, 3), Point3D(0, 2.5, 3)]
    face_1 = Face('Face1', Face3D(pts_1))
    face_2 = Face('Face2', Face3D(pts_2))
    face_3 = Face('Face3', Face3D(pts_3))
    face_4 = Face('Face4', Face3D(pts_4))
    face_5 = Face('Face5', Face3D(pts_5))
    face_6 = Face('Face6', Face3D(pts_6))
    face_7 = Face('Face7', Face3D(pts_7))
    room = Room('ZoneSHOE_BOX920980',
                [face_1, face_2, face_3, face_4, face_5, face_6, face_7],
                0.01, 1)

    assert not room.check_solid(0.01, 1, False)
    with pytest.raises(ValueError):
        room.check_solid(0.01, 1, True)


def test_init_coplanar():
    """Test the initialization of a room with coplanar faces."""
    pts_1 = [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(10, 10, 0), Point3D(10, 0, 0)]
    pts_2 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(0, 10, 0)]
    pts_3 = [Point3D(0, 0, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(0, 0, 3)]
    pts_4 = [Point3D(10, 10, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(10, 10, 3)]
    pts_5 = [Point3D(10, 10, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(10, 10, 3)]
    pts_6 = [Point3D(10, 0, 3), Point3D(10, 2.5, 3), Point3D(0, 2.5, 3), Point3D(0, 0, 3)]
    pts_7 = [Point3D(10, 2.5, 3), Point3D(10, 5, 3), Point3D(0, 5, 3), Point3D(0, 2.5, 3)]
    pts_8 = [Point3D(10, 5, 3), Point3D(10, 10, 3), Point3D(0, 10, 3), Point3D(0, 5, 3)]
    face_1 = Face('Face1', Face3D(pts_1))
    face_2 = Face('Face2', Face3D(pts_2))
    face_3 = Face('Face3', Face3D(pts_3))
    face_4 = Face('Face4', Face3D(pts_4))
    face_5 = Face('Face5', Face3D(pts_5))
    face_6 = Face('Face6', Face3D(pts_6))
    face_7 = Face('Face7', Face3D(pts_7))
    face_8 = Face('Face8', Face3D(pts_8))
    room = Room('ZoneSHOE_BOX920980',
                [face_1, face_2, face_3, face_4, face_5, face_6, face_7, face_8],
                0.01, 1)

    str(room)  # test the string representation of the room
    assert room.identifier == 'ZoneSHOE_BOX920980'
    assert room.display_name == 'ZoneSHOE_BOX920980'
    assert isinstance(room.geometry, Polyface3D)
    assert len(room.geometry.vertices) == 12
    assert len(room) == 8
    assert room.center == Point3D(5, 5, 1.5)
    assert room.volume == 300
    assert room.floor_area == 100
    assert room.exposed_area == 220
    assert room.exterior_wall_area == 120
    assert room.exterior_aperture_area == 0
    assert room.average_floor_height == 0
    assert not room.has_parent
    assert room.check_solid(0.01, 1)


def test_polyface3d_init_from_polyface():
    """Test the initialization of room from a Polyface3D."""
    bound_pts = [Point3D(0, 0), Point3D(3, 0), Point3D(3, 3), Point3D(0, 3)]
    hole_pts = [Point3D(1, 1, 0), Point3D(2, 1, 0), Point3D(2, 2, 0), Point3D(1, 2, 0)]
    face = Face3D(bound_pts, None, [hole_pts])
    polyface = Polyface3D.from_offset_face(face, 3)
    room = Room.from_polyface3d('DonutZone', polyface)

    assert room.identifier == 'DonutZone'
    assert room.display_name == 'DonutZone'
    assert isinstance(room.geometry, Polyface3D)
    assert len(room.geometry.vertices) == 16
    assert len(room) == 10
    assert room.center == Point3D(1.5, 1.5, 1.5)
    assert room.volume == 24
    assert room.floor_area == 8
    assert room.exposed_area == 56
    assert room.exterior_wall_area == 48
    assert room.exterior_aperture_area == 0
    assert room.average_floor_height == 0
    assert not room.has_parent
    assert room.check_solid(0.01, 1)


def test_init_from_box():
    """Test the initialization of a room from box."""
    room = Room.from_box('ZoneSHOE_BOX920980', 5, 10, 3, 90, Point3D(0, 0, 3))

    assert room.identifier == 'ZoneSHOE_BOX920980'
    assert room.display_name == 'ZoneSHOE_BOX920980'
    assert isinstance(room.geometry, Polyface3D)
    assert len(room.geometry.vertices) == 8
    assert len(room) == 6
    assert room.center.x == pytest.approx(5, rel=1e-3)
    assert room.center.y == pytest.approx(-2.5, rel=1e-3)
    assert room.center.z == pytest.approx(4.5, rel=1e-3)
    assert room.volume == 150
    assert room.floor_area == 50
    assert room.exposed_area == 190
    assert room.exterior_wall_area == 90
    assert room.exterior_aperture_area == 0
    assert room.average_floor_height == 3
    assert not room.has_parent
    assert room.check_solid(0.01, 1)


def test_average_orientation():
    """Test the average orientation method."""
    pts_1 = [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(10, 10, 0), Point3D(10, 0, 0)]
    pts_2 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(0, 10, 0)]
    pts_3 = [Point3D(0, 0, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(0, 0, 3)]
    pts_4 = [Point3D(10, 10, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(10, 10, 3)]
    pts_5 = [Point3D(10, 10, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(10, 10, 3)]
    pts_6 = [Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    face_1 = Face('Face1', Face3D(pts_1), boundary_condition=boundary_conditions.ground)
    face_2 = Face('Face2', Face3D(pts_2), boundary_condition=boundary_conditions.ground)
    face_3 = Face('Face3', Face3D(pts_3))
    face_4 = Face('Face4', Face3D(pts_4), boundary_condition=boundary_conditions.ground)
    face_5 = Face('Face5', Face3D(pts_5), boundary_condition=boundary_conditions.ground)
    face_6 = Face('Face6', Face3D(pts_6))
    room = Room('PassiveSolarEarthship',
                [face_1, face_2, face_3, face_4, face_5, face_6], 0.01, 1)

    assert room.average_orientation() == 180
    assert room.average_orientation(Vector2D(1, 0)) == 90


def test_room_add_prefix():
    """Test the room add_prefix method."""
    room = Room.from_box('ShoeBoxZone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.5, 0.01)
    table_geo = Face3D.from_rectangle(2, 2, Plane(o=Point3D(1.5, 4, 1)))
    room.add_indoor_shade(Shade('Table', table_geo))
    prefix = 'New'
    room.add_prefix(prefix)

    assert room.identifier.startswith(prefix)
    for face in room.faces:
        assert face.identifier.startswith(prefix)
        for ap in face.apertures:
            assert ap.identifier.startswith(prefix)
    for shd in room.shades:
        assert shd.identifier.startswith(prefix)


def test_room_multiplier():
    """Test the room multiplier."""
    room = Room.from_box('ShoeBoxZone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.5, 0.01)

    room.multiplier = 5
    assert room.multiplier == 5
    room_dup = room.duplicate()
    assert room_dup.multiplier == 5
    room_dict = room.to_dict()
    assert 'multiplier' in room_dict
    assert room_dict['multiplier'] == 5


def test_room_story():
    """Test the room multiplier."""
    room = Room.from_box('ShoeBoxZone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.5, 0.01)

    room.story = 'Floor1'
    assert room.story == 'Floor1'
    room_dup = room.duplicate()
    assert room_dup.story == 'Floor1'
    room_dict = room.to_dict()
    assert 'story' in room_dict
    assert room_dict['story'] == 'Floor1'


def test_apertures_and_shades():
    """Test the addition of apertures and shades to a room."""
    room = Room.from_box('ShoeBoxZone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.5, 0.01)
    table_geo = Face3D.from_rectangle(2, 2, Plane(o=Point3D(1.5, 4, 1)))
    room.add_indoor_shade(Shade('Table', table_geo))
    tree_canopy_geo = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(5, -3, 4)))
    room.add_outdoor_shade(Shade('TreeCanopy', tree_canopy_geo))

    assert room.exterior_aperture_area == pytest.approx(7.5, rel=1e-3)
    assert len(room.indoor_shades) == 1
    assert len(room.outdoor_shades) == 1
    assert room.indoor_shades[0].parent == room
    assert room.outdoor_shades[0].parent == room
    room.remove_indoor_shades()
    assert len(room.indoor_shades) == 0
    room.remove_outdoor_shades()
    assert len(room.outdoor_shades) == 0

    room.add_indoor_shade(Shade('Table', table_geo))
    room.add_outdoor_shade(Shade('TreeCanopy', tree_canopy_geo))
    assert len(room.indoor_shades) == 1
    assert len(room.outdoor_shades) == 1
    assert room.indoor_shades[0].has_parent
    assert room.outdoor_shades[0].has_parent
    room.remove_shades()
    assert len(room.indoor_shades) == 0
    assert len(room.outdoor_shades) == 0


def test_generate_grid():
    """Test the generate_grid method."""
    room = Room.from_box('ShoeBoxZone', 5, 10, 3)
    mesh_grid = room.generate_grid(1)
    assert len(mesh_grid.faces) == 50
    mesh_grid = room.generate_grid(0.5)
    assert len(mesh_grid.faces) == 200

    room = Room.from_box('ShoeBoxZone', 5, 10, 3, 90)
    mesh_grid = room.generate_grid(1)
    assert len(mesh_grid.faces) == 50

    room = Room.from_box('ShoeBoxZone', 5, 10, 3, 45)
    mesh_grid = room.generate_grid(1)
    assert len(mesh_grid.faces) == 50


def test_ground_by_custom_surface():
    """Test the ground_by_custom_surface method."""
    room = Room.from_box('ShoeBoxZone', 5, 10, 3, origin=Point3D(0, 0, 3))
    grd_face1 = Face3D([Point3D(-10, -10, 3), Point3D(-10, 10, 3),
                         Point3D(10, 10, 3), Point3D(10, -10, 3)])
    grd_face2 = Face3D([Point3D(-10, 10, 3), Point3D(10, 10, 3),
                         Point3D(10, 10, 6), Point3D(-10, 10, 6)])
    
    assert isinstance(room[0].boundary_condition, Outdoors)
    assert isinstance(room[1].boundary_condition, Outdoors)
    room.ground_by_custom_surface([grd_face1, grd_face2])
    assert isinstance(room[0].boundary_condition, Ground)
    assert isinstance(room[1].boundary_condition, Ground)
    for face in room[2:]:
        assert isinstance(face.boundary_condition, Outdoors)


def test_move():
    """Test the Room move method."""
    room = Room.from_box('ShoeBoxZone', 2, 2, 2)

    vec_1 = Vector3D(2, 2, 2)
    new_room = room.duplicate()
    new_room.move(vec_1)
    assert new_room.geometry.vertices[0] == Point3D(2, 2, 2)
    assert new_room.geometry.vertices[1] == Point3D(2, 4, 2)
    assert new_room.geometry.vertices[2] == Point3D(4, 4, 2)
    assert new_room.geometry.vertices[3] == Point3D(4, 2, 2)

    assert room.floor_area == new_room.floor_area
    assert room.volume == new_room.volume


def test_scale():
    """Test the Room scale method with None origin."""
    room = Room.from_box('ShoeBoxZone', 1, 1, 1, origin=Point3D(1, 1, 2))

    new_room = room.duplicate()
    new_room.scale(2)
    assert new_room.geometry.vertices[0] == Point3D(2, 2, 4)
    assert new_room.geometry.vertices[1] == Point3D(2, 4, 4)
    assert new_room.geometry.vertices[2] == Point3D(4, 4, 4)
    assert new_room.geometry.vertices[3] == Point3D(4, 2, 4)
    assert new_room.floor_area == room.floor_area * 2 ** 2
    assert new_room.volume == room.volume * 2 ** 3


def test_rotate():
    """Test the Room rotate method."""
    room = Room.from_box('ShoeBoxZone', 2, 2, 2, origin=Point3D(0, 0, 2))
    origin = Point3D(0, 0, 0)
    axis = Vector3D(1, 0, 0)

    test_1 = room.duplicate()
    test_1.rotate(axis, 180, origin)
    assert test_1.geometry.vertices[0].x == pytest.approx(0, rel=1e-3)
    assert test_1.geometry.vertices[0].y == pytest.approx(0, rel=1e-3)
    assert test_1.geometry.vertices[0].z == pytest.approx(-2, rel=1e-3)
    assert test_1.geometry.vertices[2].x == pytest.approx(2, rel=1e-3)
    assert test_1.geometry.vertices[2].y == pytest.approx(-2, rel=1e-3)
    assert test_1.geometry.vertices[2].z == pytest.approx(-2, rel=1e-3)
    assert room.floor_area == test_1.floor_area
    assert room.volume == test_1.volume
    assert len(room.geometry.vertices) == len(test_1.geometry.vertices)

    test_2 = room.duplicate()
    test_2.rotate(axis, 90, origin)
    assert test_2.geometry.vertices[0].x == pytest.approx(0, rel=1e-3)
    assert test_2.geometry.vertices[0].y == pytest.approx(-2, rel=1e-3)
    assert test_2.geometry.vertices[0].z == pytest.approx(0, rel=1e-3)
    assert test_2.geometry.vertices[2].x == pytest.approx(2, rel=1e-3)
    assert test_2.geometry.vertices[2].y == pytest.approx(-2, rel=1e-3)
    assert test_2.geometry.vertices[2].z == pytest.approx(2, rel=1e-3)
    assert room.floor_area == test_2.floor_area
    assert room.volume == test_1.volume
    assert len(room.geometry.vertices) == len(test_2.geometry.vertices)


def test_rotate_xy():
    """Test the Room rotate_xy method."""
    room = Room.from_box('ShoeBoxZone', 1, 1, 1, origin=Point3D(1, 1, 2))
    origin_1 = Point3D(1, 1, 0)

    test_1 = room.duplicate()
    test_1.rotate_xy(180, origin_1)
    assert test_1.geometry.vertices[0].x == pytest.approx(1, rel=1e-3)
    assert test_1.geometry.vertices[0].y == pytest.approx(1, rel=1e-3)
    assert test_1.geometry.vertices[0].z == pytest.approx(2, rel=1e-3)
    assert test_1.geometry.vertices[2].x == pytest.approx(0, rel=1e-3)
    assert test_1.geometry.vertices[2].y == pytest.approx(0, rel=1e-3)
    assert test_1.geometry.vertices[2].z == pytest.approx(2, rel=1e-3)

    test_2 = room.duplicate()
    room.rotate_xy(90, origin_1)
    assert test_2.geometry.vertices[0].x == pytest.approx(1, rel=1e-3)
    assert test_2.geometry.vertices[0].y == pytest.approx(1, rel=1e-3)
    assert test_1.geometry.vertices[0].z == pytest.approx(2, rel=1e-3)
    assert test_2.geometry.vertices[2].x == pytest.approx(2, rel=1e-3)
    assert test_2.geometry.vertices[2].y == pytest.approx(2, rel=1e-3)
    assert test_1.geometry.vertices[2].z == pytest.approx(2, rel=1e-3)


def test_reflect():
    """Test the Room reflect method."""
    room = Room.from_box('ShoeBoxZone', 1, 1, 1, origin=Point3D(1, 1, 2))

    origin_1 = Point3D(1, 0, 2)
    normal_1 = Vector3D(1, 0, 0)
    normal_2 = Vector3D(-1, -1, 0).normalize()

    test_1 = room.duplicate()
    test_1.reflect(Plane(normal_1, origin_1))
    assert test_1.geometry.vertices[0].x == pytest.approx(1, rel=1e-3)
    assert test_1.geometry.vertices[0].y == pytest.approx(1, rel=1e-3)
    assert test_1.geometry.vertices[0].z == pytest.approx(2, rel=1e-3)
    assert test_1.geometry.vertices[2].x == pytest.approx(0, rel=1e-3)
    assert test_1.geometry.vertices[2].y == pytest.approx(2, rel=1e-3)
    assert test_1.geometry.vertices[2].z == pytest.approx(2, rel=1e-3)

    test_1 = room.duplicate()
    test_1.reflect(Plane(normal_2, Point3D(0, 0, 2)))
    assert test_1.geometry.vertices[0].x == pytest.approx(-1, rel=1e-3)
    assert test_1.geometry.vertices[0].y == pytest.approx(-1, rel=1e-3)
    assert test_1.geometry.vertices[0].z == pytest.approx(2, rel=1e-3)
    assert test_1.geometry.vertices[2].x == pytest.approx(-2, rel=1e-3)
    assert test_1.geometry.vertices[2].y == pytest.approx(-2, rel=1e-3)
    assert test_1.geometry.vertices[2].z == pytest.approx(2, rel=1e-3)

    test_2 = room.duplicate()
    test_2.reflect(Plane(normal_2, origin_1))
    assert test_2.geometry.vertices[0].x == pytest.approx(0, rel=1e-3)
    assert test_2.geometry.vertices[0].y == pytest.approx(0, rel=1e-3)
    assert test_2.geometry.vertices[0].z == pytest.approx(2, rel=1e-3)
    assert test_2.geometry.vertices[2].x == pytest.approx(-1, rel=1e-3)
    assert test_2.geometry.vertices[2].y == pytest.approx(-1, rel=1e-3)
    assert test_2.geometry.vertices[2].z == pytest.approx(2, rel=1e-3)


def test_remove_colinear_vertices_envelope():
    """Test the remove_colinear_vertices_envelope method."""
    pts_1 = (Point3D(0, 0), Point3D(1, 0), Point3D(2, 0), Point3D(2, 2),
             Point3D(0, 2))
    pf_1 = Polyface3D.from_offset_face(Face3D(pts_1), 3)
    room_1 = Room.from_polyface3d('Zone1', pf_1)
    pts_2 = (Point3D(0.5, 2, 0.5), Point3D(1, 2, 0.5), Point3D(1.5, 2, 0.5),
             Point3D(1.5, 2, 2), Point3D(0.5, 2, 2))
    ap_2 = Aperture('TestAperture1', Face3D(pts_2))
    room_1[-3].add_aperture(ap_2)

    assert len(room_1[0].geometry.vertices) == 5
    assert len(ap_2.geometry.vertices) == 5
    room_1.remove_colinear_vertices_envelope(0.0001)
    assert len(room_1[0].geometry.vertices) == 4
    assert len(ap_2.geometry.vertices) == 4


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

    assert room_1.check_planar(0.01, False)
    assert not room_2.check_planar(0.01, False)


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

    assert room_1.check_self_intersecting(False)
    assert not room_2.check_self_intersecting(False)


def test_check_non_zero():
    """Test the check_non_zero method."""
    pts_1 = [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(10, 10, 0), Point3D(10, 0, 0)]
    pts_2 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(0, 10, 0)]
    pts_3 = [Point3D(0, 0, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(0, 0, 3)]
    pts_4 = [Point3D(10, 10, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(10, 10, 3)]
    pts_5 = [Point3D(10, 10, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(10, 10, 3)]
    pts_6 = [Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    pts_7 = [Point3D(10, 0, 3), Point3D(10, 0.0001, 3), Point3D(0, 0.0001, 3), Point3D(0, 0, 3)]
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
                  [face_1, face_2, face_3, face_4, face_5, face_6, face_7])

    assert room_1.check_non_zero(0.01, False)
    assert not room_2.check_non_zero(0.01, False)


def test_solve_adjacency():
    """Test the solve adjacency method."""
    room_south = Room.from_box('SouthZone', 5, 5, 3, origin=Point3D(0, 0, 0))
    room_north = Room.from_box('NorthZone', 5, 5, 3, origin=Point3D(0, 5, 0))

    assert room_south[1].boundary_condition == boundary_conditions.outdoors
    assert room_north[3].boundary_condition == boundary_conditions.outdoors

    adj_info = Room.solve_adjacency([room_south, room_north], 0.01)

    assert isinstance(room_south[1].boundary_condition, Surface)
    assert isinstance(room_north[3].boundary_condition, Surface)
    assert room_south[1].boundary_condition.boundary_condition_object == room_north[3].identifier
    assert room_north[3].boundary_condition.boundary_condition_object == room_south[1].identifier
    assert len(adj_info['adjacent_faces']) == 1
    assert len(adj_info['adjacent_apertures']) == 0
    assert len(adj_info['adjacent_doors']) == 0


def test_solve_adjacency_aperture():
    """Test the solve adjacency method with an interior aperture."""
    room_south = Room.from_box('SouthZone', 5, 5, 3, origin=Point3D(0, 0, 0))
    room_north = Room.from_box('NorthZone', 5, 5, 3, origin=Point3D(0, 5, 0))
    room_south[1].apertures_by_ratio(0.4, 0.01)
    room_north[3].apertures_by_ratio(0.4, 0.01)

    assert room_south[1].apertures[0].boundary_condition == boundary_conditions.outdoors
    assert room_north[3].apertures[0].boundary_condition == boundary_conditions.outdoors

    adj_info = Room.solve_adjacency([room_south, room_north], 0.01)

    assert isinstance(room_south[1].apertures[0].boundary_condition, Surface)
    assert isinstance(room_north[3].apertures[0].boundary_condition, Surface)
    assert room_south[1].apertures[0].boundary_condition.boundary_condition_object == \
        room_north[3].apertures[0].identifier
    assert room_north[3].apertures[0].boundary_condition.boundary_condition_object == \
        room_south[1].apertures[0].identifier
    assert len(adj_info['adjacent_faces']) == 1
    assert len(adj_info['adjacent_apertures']) == 1
    assert len(adj_info['adjacent_doors']) == 0


def test_find_adjacency():
    """Test the find adjacency method."""
    room_south = Room.from_box('SouthZone', 5, 5, 3, origin=Point3D(0, 0, 0))
    room_north = Room.from_box('NorthZone', 5, 5, 3, origin=Point3D(0, 5, 0))

    assert room_south[1].boundary_condition == boundary_conditions.outdoors
    assert room_north[3].boundary_condition == boundary_conditions.outdoors

    adj_faces = Room.find_adjacency([room_south, room_north], 0.01)
    assert len(adj_faces) == 1
    assert len(adj_faces[0]) == 2

    adj_info = Room.solve_adjacency([room_south, room_north], 0.01)

    # make sure it all still works after the Surface BC is already set
    adj_faces = Room.find_adjacency([room_south, room_north], 0.01)
    assert len(adj_faces) == 1
    assert len(adj_faces[0]) == 2


def test_group_by_orientation():
    """Test the group_by_orientation method."""
    pts_1 = (Point3D(0, 0), Point3D(15, 0), Point3D(10, 5), Point3D(5, 5))
    pts_2 = (Point3D(15, 0), Point3D(15, 15), Point3D(10, 10), Point3D(10, 5))
    pts_3 = (Point3D(0, 15), Point3D(5, 10), Point3D(10, 10), Point3D(15, 15))
    pts_4 = (Point3D(0, 0), Point3D(5, 5), Point3D(5, 10), Point3D(0, 15))
    pts_5 = (Point3D(5, 5), Point3D(10, 5), Point3D(10, 10), Point3D(5, 10))
    pf_1 = Polyface3D.from_offset_face(Face3D(pts_1), 3)
    pf_2 = Polyface3D.from_offset_face(Face3D(pts_2), 3)
    pf_3 = Polyface3D.from_offset_face(Face3D(pts_3), 3)
    pf_4 = Polyface3D.from_offset_face(Face3D(pts_4), 3)
    pf_5 = Polyface3D.from_offset_face(Face3D(pts_5), 3)
    room_1 = Room.from_polyface3d('Zone1', pf_1)
    room_2 = Room.from_polyface3d('Zone2', pf_2)
    room_3 = Room.from_polyface3d('Zone3', pf_3)
    room_4 = Room.from_polyface3d('Zone4', pf_4)
    room_5 = Room.from_polyface3d('Zone5', pf_5)

    rooms = [room_1, room_2, room_3, room_4, room_5]
    adj_info = Room.solve_adjacency(rooms, 0.01)
    grouped_rooms, core_rooms, orientations = Room.group_by_orientation(rooms)

    assert len(grouped_rooms) == 4
    assert len(core_rooms) == 1
    assert orientations == [0.0, 90.0, 180.0, 270.0]


def test_to_dict():
    """Test the Room to_dict method."""
    room = Room.from_box('ShoeBoxZone', 5, 10, 3)
    room.display_name = 'Shoe Box Zone'

    rd = room.to_dict()
    assert rd['type'] == 'Room'
    assert rd['identifier'] == 'ShoeBoxZone'
    assert rd['display_name'] == 'Shoe Box Zone'
    assert 'faces' in rd
    assert len(rd['faces']) == 6
    assert 'indoor_shades' not in rd
    assert 'outdoor_shades' not in rd
    assert 'properties' in rd
    assert rd['properties']['type'] == 'RoomProperties'


def test_to_from_dict():
    """Test the to/from dict of Room objects."""
    room = Room.from_box('ShoeBoxZone', 5, 10, 3)

    room_dict = room.to_dict()
    new_room = Room.from_dict(room_dict)
    assert isinstance(new_room, Room)
    assert new_room.to_dict() == room_dict


def test_writer():
    """Test the Room writer object."""
    room = Room.from_box('ShoeBoxZone', 5, 10, 3)

    writers = [mod for mod in dir(room.to) if not mod.startswith('_')]
    for writer in writers:
        assert callable(getattr(room.to, writer))
