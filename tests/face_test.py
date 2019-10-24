"""Test Face class."""
from honeybee.face import Face
from honeybee.facetype import face_types, Wall
from honeybee.boundarycondition import boundary_conditions, Outdoors
from honeybee.aperture import Aperture
from honeybee.door import Door
from honeybee.shade import Shade

from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.plane import Plane

import pytest


def test_init():
    """Test the initialization of a Face."""
    vertices = [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    face = Face('Wall: SIM_INT_AIR [920980]', Face3D(vertices))

    assert face.name == 'WallSIM_INT_AIR920980'
    assert face.display_name == 'Wall: SIM_INT_AIR [920980]'
    assert isinstance(face.geometry, Face3D)
    assert len(face.vertices) == 4
    assert face.upper_left_vertices[0] == Point3D(0, 0, 3)
    assert face.normal == Vector3D(1, 0, 0)
    assert face.center == Point3D(0, 5, 1.5)
    assert face.area == 30
    assert face.perimeter == 26
    assert isinstance(face.boundary_condition, Outdoors)
    assert isinstance(face.type, Wall)
    assert not face.has_parent


def test_default_face_type():
    """Test the auto-assigning of face type by normal."""
    vertices_wall = [[0, 0, 0], [0, 10, 0], [0, 10, 3], [0, 0, 3]]
    vertices_floor = [[0, 0, 0], [0, 10, 0], [10, 10, 0], [10, 0, 0]]
    vertices_roof = list(reversed(vertices_floor))

    wf = Face.from_vertices('wall', vertices_wall)
    assert wf.type == wf.TYPES.wall
    rf = Face.from_vertices('roof', vertices_roof)
    assert rf.type == rf.TYPES.roof_ceiling
    ff = Face.from_vertices('floor', vertices_floor)
    assert ff.type == ff.TYPES.floor


def test_setting_face_type():
    """Test the setting of face type to override default."""
    vertices = [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    face = Face('Vertical Roof', Face3D(vertices), face_types.roof_ceiling)

    assert face.type == face_types.roof_ceiling
    face.type = face_types.wall
    assert face.type == face_types.wall


def test_default_boundary_condition():
    """Test the auto-assigning of face boundary condition by normal."""
    vertices_above = \
        [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    vertices_mid = \
        [Point3D(0, 0, -1), Point3D(0, 10, -1), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    vertices_below = \
        [Point3D(0, 0, -3), Point3D(0, 10, -3), Point3D(0, 10, 0), Point3D(0, 0, 0)]
    face_above = Face('Wall Above', Face3D(vertices_above))
    face_mid = Face('Wall Mid', Face3D(vertices_mid))
    face_below = Face('Wall Below', Face3D(vertices_below))

    assert face_above.boundary_condition == boundary_conditions.outdoors
    assert face_mid.boundary_condition == boundary_conditions.outdoors
    assert face_below.boundary_condition == boundary_conditions.ground


def test_set_boundary_condition():
    """Test the setting of boundary condition to override default."""
    vertices = [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    face = Face('Wall', Face3D(vertices), face_types.wall, boundary_conditions.ground)

    assert face.boundary_condition == boundary_conditions.ground
    face.boundary_condition = boundary_conditions.outdoors
    assert face.boundary_condition == boundary_conditions.outdoors


def test_face_duplicate():
    """Test the duplication of Face objects."""
    pts = (Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 0, 0))
    face_1 = Aperture('Test Face', Face3D(pts))
    face_2 = face_1.duplicate()

    assert face_1 is not face_2
    for i, pt in enumerate(face_1.vertices):
        assert pt == face_2.vertices[i]
    assert face_1.name == face_2.name

    face_2.move(Vector3D(0, 1, 0))
    for i, pt in enumerate(face_1.vertices):
        assert pt != face_2.vertices[i]


def test_horizontal_orientation():
    """Test the Face horizontal_orientation method."""
    pts_1 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 0, 0)]
    pts_2 = tuple(reversed(pts_1))
    pts_3 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(0, 5, 3), Point3D(0, 5, 0)]
    pts_4 = tuple(reversed(pts_3))

    face_1 = Face('Test Face', Face3D(pts_1))
    face_2 = Face('Test Face', Face3D(pts_2))
    face_3 = Face('Test Face', Face3D(pts_3))
    face_4 = Face('Test Face', Face3D(pts_4))

    assert face_1.horizontal_orientation() == 0
    assert face_2.horizontal_orientation() == 180
    assert face_3.horizontal_orientation() == 270
    assert face_4.horizontal_orientation() == 90


def test_cardinal_direction():
    """Test the Face cardinal_direction method."""
    pts_1 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 0, 0)]
    pts_2 = tuple(reversed(pts_1))
    pts_3 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(0, 5, 3), Point3D(0, 5, 0)]
    pts_4 = tuple(reversed(pts_3))

    face_1 = Face('Test Face', Face3D(pts_1))
    face_2 = Face('Test Face', Face3D(pts_2))
    face_3 = Face('Test Face', Face3D(pts_3))
    face_4 = Face('Test Face', Face3D(pts_4))

    assert face_1.cardinal_direction() == 'North'
    assert face_2.cardinal_direction() == 'South'
    assert face_3.cardinal_direction() == 'West'
    assert face_4.cardinal_direction() == 'East'


def test_add_remove_door():
    """Test the adding and removing of an door to a Face."""
    face_face3d = Face3D.from_rectangle(10, 10, Plane(o=Point3D(0, 0, 3)))
    ap_face3d = Face3D.from_rectangle(2, 2, Plane(o=Point3D(2, 2, 3)))
    face = Face('Test_Roof', face_face3d)
    door = Door('Test_Trap_Door', ap_face3d)
    face.add_door(door)

    assert len(face.doors) == 1
    assert len(face.doors[0].geometry.vertices) == 4
    assert face.doors[0].area == pytest.approx(4, rel=1e-2)
    assert face.doors[0].parent is face
    assert len(face.punched_vertices) == 10
    assert face.punched_geometry.area == 96
    assert face.check_doors_valid(0.01, 1)

    face.remove_doors()
    assert len(face.doors) == 0
    assert len(face.punched_vertices) == 4
    assert face.punched_geometry.area == 100


def test_add_remove_doors():
    """Test the adding and removing of multiple doors to a Face."""
    face_face3d = Face3D.from_rectangle(10, 10, Plane(o=Point3D(0, 0, 3)))
    ap_face3d_1 = Face3D.from_rectangle(2, 2, Plane(o=Point3D(2, 2, 3)))
    ap_face3d_2 = Face3D.from_rectangle(2, 2, Plane(o=Point3D(7, 7, 3)))
    face = Face('Test_Roof', face_face3d)
    door_1 = Door('Test_Trap_Door_1', ap_face3d_1)
    door_2 = Door('Test_Trap_Door_2', ap_face3d_2)
    face.add_doors([door_1, door_2])

    assert len(face.doors) == 2
    assert face.doors[0].parent is face
    assert face.doors[1].parent is face
    assert len(face.punched_vertices) == 16
    assert face.punched_geometry.area == 92
    assert face.check_doors_valid(0.01, 1)

    face.remove_doors()
    assert len(face.doors) == 0
    assert len(face.punched_vertices) == 4
    assert face.punched_geometry.area == 100


def test_add_remove_aperture():
    """Test the adding and removing of an aperture to a Face."""
    face_face3d = Face3D.from_rectangle(10, 10, Plane(o=Point3D(0, 0, 3)))
    ap_face3d = Face3D.from_rectangle(2, 2, Plane(o=Point3D(2, 2, 3)))
    face = Face('Test_Roof', face_face3d)
    aperture = Aperture('Test_Skylight', ap_face3d)
    face.add_aperture(aperture)

    assert len(face.apertures) == 1
    assert len(face.apertures[0].geometry.vertices) == 4
    assert face.apertures[0].area == pytest.approx(4, rel=1e-2)
    assert face.apertures[0].parent is face
    assert len(face.punched_vertices) == 10
    assert face.punched_geometry.area == 96
    assert face.check_apertures_valid(0.01, 1)

    face.remove_apertures()
    assert len(face.apertures) == 0
    assert len(face.punched_vertices) == 4
    assert face.punched_geometry.area == 100


def test_add_remove_apertures():
    """Test the adding and removing of multiple apertures to a Face."""
    face_face3d = Face3D.from_rectangle(10, 10, Plane(o=Point3D(0, 0, 3)))
    ap_face3d_1 = Face3D.from_rectangle(2, 2, Plane(o=Point3D(2, 2, 3)))
    ap_face3d_2 = Face3D.from_rectangle(2, 2, Plane(o=Point3D(7, 7, 3)))
    face = Face('Test_Roof', face_face3d)
    aperture_1 = Aperture('Test_Skylight_1', ap_face3d_1)
    aperture_2 = Aperture('Test_Skylight_2', ap_face3d_2)
    face.add_apertures([aperture_1, aperture_2])

    assert len(face.apertures) == 2
    assert face.apertures[0].parent is face
    assert face.apertures[1].parent is face
    assert len(face.punched_vertices) == 16
    assert face.punched_geometry.area == 92
    assert face.check_apertures_valid(0.01, 1)

    face.remove_apertures()
    assert len(face.apertures) == 0
    assert len(face.punched_vertices) == 4
    assert face.punched_geometry.area == 100


def test_add_remove_sub_faces():
    """Test the adding and removing of an aperture and a door to a Face."""
    face_face3d = Face3D.from_rectangle(10, 10, Plane(o=Point3D(0, 0, 3)))
    ap_face3d = Face3D.from_rectangle(2, 2, Plane(o=Point3D(2, 2, 3)))
    dr_face3d = Face3D.from_rectangle(2, 2, Plane(o=Point3D(7, 7, 3)))
    face = Face('Test_Roof', face_face3d)
    aperture = Aperture('Test_Skylight', ap_face3d)
    door = Door('Test_Trap_Door', dr_face3d)
    face.add_aperture(aperture)
    face.add_door(door)

    assert len(face.apertures) == 1
    assert len(face.doors) == 1
    assert face.apertures[0].parent is face
    assert face.doors[0].parent is face
    assert len(face.punched_vertices) == 16
    assert face.punched_geometry.area == 92
    assert face.check_sub_faces_valid(0.01, 1)

    face.remove_sub_faces()
    assert len(face.apertures) == 0
    assert len(face.punched_vertices) == 4
    assert face.punched_geometry.area == 100


def test_sub_faces_invalid():
    """Test the adding and removing of invalid sub-faces."""
    face_face3d = Face3D.from_rectangle(10, 10, Plane(o=Point3D(0, 0, 3)))
    ap_face3d = Face3D.from_rectangle(2, 2, Plane(o=Point3D(2, 2, 3)))
    dr_face3d = Face3D.from_rectangle(2, 2, Plane(o=Point3D(7, 7, 3)))
    dr_face3d_invalid_1 = Face3D.from_rectangle(2, 2, Plane(o=Point3D(7, 7, 1)))
    dr_face3d_invalid_2 = \
        Face3D([Point3D(0, 0, 0), Point3D(0, 1, 0), Point3D(0, 1, 3), Point3D(0, 0, 3)])

    face = Face('Test_Roof', face_face3d)
    aperture = Aperture('Test_Skylight', ap_face3d)
    door = Door('Test_Trap_Door', dr_face3d)
    invalid_aperture_1 = Aperture('Test_Skylight', dr_face3d_invalid_1)
    invalid_aperture_2 = Aperture('Test_Skylight', dr_face3d_invalid_2)

    with pytest.raises(AssertionError):
        face.add_aperture(door)
    with pytest.raises(AssertionError):
        face.add_door(aperture)

    face.add_aperture(invalid_aperture_1)
    with pytest.raises(ValueError):
        face.check_apertures_valid(0.01, 1)
    face.remove_apertures()

    face.add_aperture(invalid_aperture_2)
    with pytest.raises(ValueError):
        face.check_apertures_valid(0.01, 1)


def test_sub_faces_invalid_boundary_condition():
    """Test the adding of a sub-face to a face with invalid boundary conditions."""
    face_face3d = Face3D.from_rectangle(10, 10, Plane(o=Point3D(0, 0, 3)))
    ap_face3d = Face3D.from_rectangle(2, 2, Plane(o=Point3D(2, 2, 3)))
    dr_face3d = Face3D.from_rectangle(2, 2, Plane(o=Point3D(7, 7, 3)))

    face = Face('Test_Roof', face_face3d, face_types.wall, boundary_conditions.ground)
    aperture = Aperture('Test_Skylight', ap_face3d)
    door = Door('Test_Trap_Door', dr_face3d)

    with pytest.raises(AssertionError):
        face.add_aperture(aperture)
    with pytest.raises(AssertionError):
        face.add_door(door)


def test_sub_faces_invalid_face_type():
    """Test the adding of a sub-face to a face with invalid face type."""
    face_face3d = Face3D.from_rectangle(10, 10, Plane(o=Point3D(0, 0, 3)))
    ap_face3d = Face3D.from_rectangle(2, 2, Plane(o=Point3D(2, 2, 3)))
    dr_face3d = Face3D.from_rectangle(2, 2, Plane(o=Point3D(7, 7, 3)))

    face = Face('Test_Roof', face_face3d, face_types.air_wall)
    aperture = Aperture('Test_Skylight', ap_face3d)
    door = Door('Test_Trap_Door', dr_face3d)

    with pytest.raises(AssertionError):
        face.add_aperture(aperture)
    with pytest.raises(AssertionError):
        face.add_door(door)


def test_apertures_by_ratio():
    """Test the adding of apertures by ratio."""
    pts = (Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 0, 0))
    face = Face('Test_Wall', Face3D(pts))
    face.apertures_by_ratio(0.4, 0.01)

    assert len(face.apertures) == 1
    assert len(face.apertures[0].geometry.vertices) == 4
    assert sum([ap.area for ap in face.apertures]) == pytest.approx(15 * 0.4, rel=1e-2)
    assert face.punched_geometry.area == pytest.approx(15 * 0.6, rel=1e-2)


def test_apertures_by_ratio_rectangle():
    """Test the adding of apertures by ratio with rectangle apertures."""
    pts = (Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 0, 0))
    face = Face('Test_Wall', Face3D(pts))
    face.apertures_by_ratio_rectangle(0.4, 2, 0.7, 1.5, 0, 0.01)

    assert len(face.apertures) == 3
    assert len(face.apertures[0].geometry.vertices) == 4
    assert sum([ap.area for ap in face.apertures]) == pytest.approx(15 * 0.4, rel=1e-2)
    assert face.punched_geometry.area == pytest.approx(15 * 0.6, rel=1e-2)
    assert face.apertures[0].geometry.min.z == 0.7
    assert face.apertures[0].geometry.max.z - face.apertures[0].geometry.min.z == 2


def test_apertures_by_width_height():
    """Test the adding of apertures by width and height."""
    pts = (Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 0, 0))
    face = Face('Test_Wall', Face3D(pts))
    face.aperture_by_width_height(4, 2, 0.7)

    assert len(face.apertures) == 1
    assert len(face.apertures[0].geometry.vertices) == 4
    assert face.apertures[0].area == pytest.approx(8, rel=1e-2)


def test_face_overhang():
    """Test the creation of an overhang for Face objects."""
    pts_1 = (Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 0, 0))
    pts_2 = (Point3D(0, 0, 0), Point3D(2, 0, 3), Point3D(4, 0, 3))
    pts_3 = (Point3D(0, 0, 0), Point3D(2, 0, 3), Point3D(4, 0, 0))
    face_1 = Face('Rectangle Face', Face3D(pts_1))
    face_2 = Face('Good Triangle Face', Face3D(pts_2))
    face_3 = Face('Bad Triangle Face', Face3D(pts_3))
    face_1.overhang(1, tolerance=0.01)
    face_2.overhang(1, tolerance=0.01)
    face_3.overhang(1, tolerance=0.01)
    assert isinstance(face_1.outdoor_shades[0], Shade)
    assert isinstance(face_2.outdoor_shades[0], Shade)
    assert len(face_3.outdoor_shades) == 0
    assert face_1.outdoor_shades[0].has_parent
    assert face_2.outdoor_shades[0].has_parent


def test_face_louvers_by_distance_between():
    """Test the creation of a louvers_by_distance_between for Face objects."""
    pts_1 = (Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 0, 0))
    face = Face('Rectangle Face', Face3D(pts_1))
    face.louvers_by_distance_between(0.5, 0.2, 0.1)

    assert len(face.outdoor_shades) == 6
    for louver in face.outdoor_shades:
        assert isinstance(louver, Shade)
        assert louver.area == 5 * 0.2
        assert louver.has_parent


def test_move():
    """Test the Face move method."""
    pts_1 = (Point3D(0, 0, 0), Point3D(2, 0, 0), Point3D(2, 2, 0), Point3D(0, 2, 0))
    plane_1 = Plane(Vector3D(0, 0, 1), Point3D(0, 0, 0))
    face = Face('Rectangle Face', Face3D(pts_1, plane_1))

    vec_1 = Vector3D(2, 2, 2)
    new_f = face.duplicate()
    new_f.move(vec_1)
    assert new_f.geometry[0] == Point3D(2, 2, 2)
    assert new_f.geometry[1] == Point3D(4, 2, 2)
    assert new_f.geometry[2] == Point3D(4, 4, 2)
    assert new_f.geometry[3] == Point3D(2, 4, 2)
    assert new_f.normal == face.normal
    assert face.area == new_f.area
    assert face.perimeter == new_f.perimeter


def test_scale():
    """Test the Face scale method."""
    pts = (Point3D(1, 1, 2), Point3D(2, 1, 2), Point3D(2, 2, 2), Point3D(1, 2, 2))
    plane = Plane(Vector3D(0, 0, 1), Point3D(0, 0, 2))
    face = Face('Rectangle Face', Face3D(pts, plane))

    new_f = face.duplicate()
    new_f.scale(2)
    assert new_f.geometry[0] == Point3D(2, 2, 4)
    assert new_f.geometry[1] == Point3D(4, 2, 4)
    assert new_f.geometry[2] == Point3D(4, 4, 4)
    assert new_f.geometry[3] == Point3D(2, 4, 4)
    assert new_f.area == face.area * 2 ** 2
    assert new_f.perimeter == face.perimeter * 2
    assert new_f.normal == face.normal


def test_rotate():
    """Test the Face rotate method."""
    pts = (Point3D(0, 0, 2), Point3D(2, 0, 2), Point3D(2, 2, 2), Point3D(0, 2, 2))
    plane = Plane(Vector3D(0, 0, 1), Point3D(0, 0, 2))
    face = Face('Rectangle Face', Face3D(pts, plane))
    origin = Point3D(0, 0, 0)
    axis = Vector3D(1, 0, 0)

    test_1 = face.duplicate()
    test_1.rotate(axis, 180, origin)
    assert test_1.geometry[0].x == pytest.approx(0, rel=1e-3)
    assert test_1.geometry[0].y == pytest.approx(0, rel=1e-3)
    assert test_1.geometry[0].z == pytest.approx(-2, rel=1e-3)
    assert test_1.geometry[2].x == pytest.approx(2, rel=1e-3)
    assert test_1.geometry[2].y == pytest.approx(-2, rel=1e-3)
    assert test_1.geometry[2].z == pytest.approx(-2, rel=1e-3)
    assert face.area == test_1.area
    assert len(face.vertices) == len(test_1.vertices)

    test_2 = face.duplicate()
    test_2.rotate(axis, 90, origin)
    assert test_2.geometry[0].x == pytest.approx(0, rel=1e-3)
    assert test_2.geometry[0].y == pytest.approx(-2, rel=1e-3)
    assert test_2.geometry[0].z == pytest.approx(0, rel=1e-3)
    assert test_2.geometry[2].x == pytest.approx(2, rel=1e-3)
    assert test_2.geometry[2].y == pytest.approx(-2, rel=1e-3)
    assert test_2.geometry[2].z == pytest.approx(2, rel=1e-3)
    assert face.area == test_2.area
    assert len(face.vertices) == len(test_2.vertices)


def test_rotate_xy():
    """Test the Face rotate_xy method."""
    pts = (Point3D(1, 1, 2), Point3D(2, 1, 2), Point3D(2, 2, 2), Point3D(1, 2, 2))
    plane = Plane(Vector3D(0, 0, 1), Point3D(0, 0, 2))
    face = Face('Rectangle Face', Face3D(pts, plane))
    origin_1 = Point3D(1, 1, 0)

    test_1 = face.duplicate()
    test_1.rotate_xy(180, origin_1)
    assert test_1.geometry[0].x == pytest.approx(1, rel=1e-3)
    assert test_1.geometry[0].y == pytest.approx(1, rel=1e-3)
    assert test_1.geometry[0].z == pytest.approx(2, rel=1e-3)
    assert test_1.geometry[2].x == pytest.approx(0, rel=1e-3)
    assert test_1.geometry[2].y == pytest.approx(0, rel=1e-3)
    assert test_1.geometry[2].z == pytest.approx(2, rel=1e-3)

    test_2 = face.duplicate()
    test_2.rotate_xy(90, origin_1)
    assert test_2.geometry[0].x == pytest.approx(1, rel=1e-3)
    assert test_2.geometry[0].y == pytest.approx(1, rel=1e-3)
    assert test_1.geometry[0].z == pytest.approx(2, rel=1e-3)
    assert test_2.geometry[2].x == pytest.approx(0, rel=1e-3)
    assert test_2.geometry[2].y == pytest.approx(2, rel=1e-3)
    assert test_1.geometry[2].z == pytest.approx(2, rel=1e-3)


def test_reflect():
    """Test the Face reflect method."""
    pts = (Point3D(1, 1, 2), Point3D(2, 1, 2), Point3D(2, 2, 2), Point3D(1, 2, 2))
    plane = Plane(Vector3D(0, 0, 1), Point3D(0, 0, 2))
    face = Face('Rectangle Face', Face3D(pts, plane))

    origin_1 = Point3D(1, 0, 2)
    origin_2 = Point3D(0, 0, 2)
    normal_1 = Vector3D(1, 0, 0)
    normal_2 = Vector3D(-1, -1, 0).normalize()
    plane_1 = Plane(normal_1, origin_1)
    plane_2 = Plane(normal_2, origin_2)
    plane_3 = Plane(normal_2, origin_1)

    test_1 = face.duplicate()
    test_1.reflect(plane_1)
    assert test_1.geometry[-1].x == pytest.approx(1, rel=1e-3)
    assert test_1.geometry[-1].y == pytest.approx(1, rel=1e-3)
    assert test_1.geometry[-1].z == pytest.approx(2, rel=1e-3)
    assert test_1.geometry[1].x == pytest.approx(0, rel=1e-3)
    assert test_1.geometry[1].y == pytest.approx(2, rel=1e-3)
    assert test_1.geometry[1].z == pytest.approx(2, rel=1e-3)

    test_1 = face.duplicate()
    test_1.reflect(plane_2)
    assert test_1.geometry[-1].x == pytest.approx(-1, rel=1e-3)
    assert test_1.geometry[-1].y == pytest.approx(-1, rel=1e-3)
    assert test_1.geometry[-1].z == pytest.approx(2, rel=1e-3)
    assert test_1.geometry[1].x == pytest.approx(-2, rel=1e-3)
    assert test_1.geometry[1].y == pytest.approx(-2, rel=1e-3)
    assert test_1.geometry[1].z == pytest.approx(2, rel=1e-3)

    test_2 = face.duplicate()
    test_2.reflect(plane_3)
    assert test_2.geometry[-1].x == pytest.approx(0, rel=1e-3)
    assert test_2.geometry[-1].y == pytest.approx(0, rel=1e-3)
    assert test_2.geometry[-1].z == pytest.approx(2, rel=1e-3)
    assert test_2.geometry[1].x == pytest.approx(-1, rel=1e-3)
    assert test_2.geometry[1].y == pytest.approx(-1, rel=1e-3)
    assert test_2.geometry[1].z == pytest.approx(2, rel=1e-3)


def test_check_planar():
    """Test the check_planar method."""
    pts_1 = (Point3D(0, 0, 2), Point3D(2, 0, 2), Point3D(2, 2, 2), Point3D(0, 2, 2))
    pts_2 = (Point3D(0, 0, 0), Point3D(2, 0, 2), Point3D(2, 2, 2), Point3D(0, 2, 2))
    pts_3 = (Point3D(0, 0, 2.0001), Point3D(2, 0, 2), Point3D(2, 2, 2), Point3D(0, 2, 2))
    plane_1 = Plane(Vector3D(0, 0, 1), Point3D(0, 0, 2))
    face_1 = Face('Wall 1', Face3D(pts_1, plane_1))
    face_2 = Face('Wall 2', Face3D(pts_2, plane_1))
    face_3 = Face('Wall 3', Face3D(pts_3, plane_1))

    assert face_1.check_planar(0.001) is True
    assert face_2.check_planar(0.001, False) is False
    with pytest.raises(Exception):
        face_2.check_planar(0.0001)
    assert face_3.check_planar(0.001) is True
    assert face_3.check_planar(0.000001, False) is False
    with pytest.raises(Exception):
        face_3.check_planar(0.000001)


def test_check_self_intersecting():
    """Test the check_self_intersecting method."""
    plane_1 = Plane(Vector3D(0, 0, 1))
    plane_2 = Plane(Vector3D(0, 0, -1))
    pts_1 = (Point3D(0, 0), Point3D(2, 0), Point3D(2, 2), Point3D(0, 2))
    pts_2 = (Point3D(0, 0), Point3D(0, 2), Point3D(2, 0), Point3D(2, 2))
    face_1 = Face('Wall 1', Face3D(pts_1, plane_1))
    face_2 = Face('Wall 2', Face3D(pts_2, plane_1))
    face_3 = Face('Wall 3', Face3D(pts_1, plane_2))
    face_4 = Face('Wall 4', Face3D(pts_2, plane_2))

    assert face_1.check_self_intersecting(False) is True
    assert face_2.check_self_intersecting(False) is False
    with pytest.raises(Exception):
        assert face_2.check_self_intersecting(True)
    assert face_3.check_self_intersecting(False) is True
    assert face_4.check_self_intersecting(False) is False
    with pytest.raises(Exception):
        assert face_4.check_self_intersecting(True)


def test_check_non_zero():
    """Test the check_non_zero method."""
    plane_1 = Plane(Vector3D(0, 0, 1))
    pts_1 = (Point3D(0, 0), Point3D(2, 0), Point3D(2, 2))
    pts_2 = (Point3D(0, 0), Point3D(2, 0), Point3D(2, 0))
    face_1 = Face('Wall 1', Face3D(pts_1, plane_1))
    face_2 = Face('Wall 2', Face3D(pts_2, plane_1))

    assert face_1.check_non_zero(0.0001, False) is True
    assert face_2.check_non_zero(0.0001, False) is False
    with pytest.raises(Exception):
        assert face_2.check_self_intersecting(0.0001, True)


def test_to_dict():
    """Test the Face to_dict method."""
    vertices = [[0, 0, 0], [0, 10, 0], [0, 10, 3], [0, 0, 3]]
    face = Face.from_vertices('test wall', vertices, face_types.wall,
                              boundary_conditions.ground)

    fd = face.to_dict()
    assert fd['type'] == 'Face'
    assert fd['name'] == 'testwall'
    assert fd['display_name'] == 'test wall'
    assert 'geometry' in fd
    assert len(fd['geometry']['boundary']) == len(vertices)
    assert 'properties' in fd
    assert fd['properties']['type'] == 'FaceProperties'
    assert fd['face_type'] == 'Wall'
    assert fd['boundary_condition']['type'] == 'Ground'


def test_to_from_dict():
    """Test the to/from dict of Face objects."""
    vertices = [[0, 0, 0], [0, 10, 0], [0, 10, 3], [0, 0, 3]]
    face = Face.from_vertices('test wall', vertices, face_types.wall,
                              boundary_conditions.ground)

    face_dict = face.to_dict()
    new_face = Face.from_dict(face_dict)
    assert isinstance(new_face, Face)
    assert new_face.to_dict() == face_dict


def test_writer():
    """Test the Face writer object."""
    vertices = [[0, 0, 0], [0, 10, 0], [0, 10, 3], [0, 0, 3]]
    face = Face.from_vertices('test wall', vertices, face_types.wall,
                              boundary_conditions.ground)

    writers = [mod for mod in dir(face.to) if not mod.startswith('_')]
    for writer in writers:
        assert callable(getattr(face.to, writer))
