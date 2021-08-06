"""Test the Aperture class."""
from honeybee.aperture import Aperture
from honeybee.shade import Shade
from honeybee.boundarycondition import Outdoors

from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.geometry3d.plane import Plane
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D

import uuid as py_uuid
import pytest


def test_aperture_init():
    """Test the initialization of Aperture objects."""
    pts = (Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 0, 0))
    unique_id = str(py_uuid.uuid4())
    aperture = Aperture(unique_id, Face3D(pts))
    aperture.display_name = 'Test Window'
    str(aperture)  # test the string representation

    assert aperture.identifier == unique_id
    assert aperture.display_name == 'Test Window'
    assert isinstance(aperture.geometry, Face3D)
    assert len(aperture.vertices) == 4
    assert aperture.upper_left_vertices[0] == Point3D(5, 0, 3)
    assert len(aperture.triangulated_mesh3d.faces) == 2
    assert aperture.normal == Vector3D(0, 1, 0)
    assert aperture.center == Point3D(2.5, 0, 1.5)
    assert aperture.area == 15
    assert aperture.perimeter == 16
    assert isinstance(aperture.boundary_condition, Outdoors)
    assert not aperture.is_operable
    assert not aperture.has_parent
    assert aperture.top_level_parent is None


def test_aperture_from_vertices():
    """Test the initialization of Aperture objects from vertices."""
    pts = (Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 0, 0))
    unique_id = str(py_uuid.uuid4())
    aperture = Aperture.from_vertices(unique_id, pts)
    aperture.display_name = 'Test Window'

    assert aperture.identifier == unique_id
    assert aperture.display_name == 'Test Window'
    assert isinstance(aperture.geometry, Face3D)
    assert len(aperture.vertices) == 4
    assert aperture.upper_left_vertices[0] == Point3D(5, 0, 3)
    assert len(aperture.triangulated_mesh3d.faces) == 2
    assert aperture.normal == Vector3D(0, 1, 0)
    assert aperture.center == Point3D(2.5, 0, 1.5)
    assert aperture.area == 15
    assert aperture.perimeter == 16
    assert isinstance(aperture.boundary_condition, Outdoors)
    assert aperture.is_operable is False
    assert not aperture.has_parent


def test_aperture_duplicate():
    """Test the duplication of Aperture objects."""
    pts = (Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 0, 0))
    ap_1 = Aperture('TestWindow', Face3D(pts))
    ap_2 = ap_1.duplicate()

    assert ap_1 is not ap_2
    for i, pt in enumerate(ap_1.vertices):
        assert pt == ap_2.vertices[i]
    assert ap_1.identifier == ap_2.identifier
    assert ap_1.display_name == ap_2.display_name

    ap_2.move(Vector3D(0, 1, 0))
    for i, pt in enumerate(ap_1.vertices):
        assert pt != ap_2.vertices[i]


def test_aperture_add_shade():
    """Test the addition of shade Aperture objects."""
    pts_1 = (Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 0, 0))
    pts_2 = (Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 2, 3))

    aperture = Aperture('RectangleWindow', Face3D(pts_1))
    shade = Shade('TriangleShade', Face3D(pts_2), is_detached=True)
    assert shade.is_detached
    assert not shade.is_indoor

    aperture.add_indoor_shade(shade)
    assert shade.has_parent
    assert shade.parent.identifier == aperture.identifier
    assert not shade.is_detached
    assert shade.is_indoor


def test_aperture_add_prefix():
    """Test the aperture add_prefix method."""
    pts_1 = (Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 0, 0))
    aperture = Aperture('RectangleWindow', Face3D(pts_1))
    aperture.extruded_border(0.1)
    prefix = 'New'
    aperture.add_prefix(prefix)

    assert aperture.identifier.startswith(prefix)
    for shd in aperture.shades:
        assert shd.identifier.startswith(prefix)


def test_aperture_overhang():
    """Test the creation of an overhang for Aperture objects."""
    pts_1 = (Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 0, 0))
    pts_2 = (Point3D(0, 0, 0), Point3D(2, 0, 3), Point3D(4, 0, 3))
    pts_3 = (Point3D(0, 0, 0), Point3D(2, 0, 3), Point3D(4, 0, 0))
    aperture_1 = Aperture('RectangleWindow', Face3D(pts_1))
    aperture_2 = Aperture('GoodTriangleWindow', Face3D(pts_2))
    aperture_3 = Aperture('BadTriangleWindow', Face3D(pts_3))
    aperture_1.overhang(1, tolerance=0.01)
    aperture_2.overhang(1, indoor=True, tolerance=0.01)
    aperture_3.overhang(1, tolerance=0.01)
    assert isinstance(aperture_1.outdoor_shades[0], Shade)
    assert isinstance(aperture_2.indoor_shades[0], Shade)
    assert len(aperture_3.outdoor_shades) == 0
    assert aperture_1.outdoor_shades[0].has_parent
    assert aperture_2.indoor_shades[0].has_parent
    assert not aperture_1.outdoor_shades[0].is_indoor
    assert aperture_2.indoor_shades[0].is_indoor


def test_aperture_fin():
    """Test the creation of a fins for Aperture objects."""
    pts_1 = (Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 0, 0))
    pts_2 = (Point3D(0, 0, 0), Point3D(2, 0, 3), Point3D(4, 0, 3))
    aperture_1 = Aperture('RectangleWindow', Face3D(pts_1))
    aperture_2 = Aperture('TriangleWindow', Face3D(pts_2))
    aperture_1.right_fin(1, tolerance=0.01)
    aperture_2.right_fin(1, tolerance=0.01)
    aperture_1.left_fin(1, tolerance=0.01)
    aperture_2.left_fin(1, tolerance=0.01)
    assert len(aperture_1.outdoor_shades) == 2
    assert isinstance(aperture_1.outdoor_shades[0], Shade)
    assert aperture_1.outdoor_shades[0].has_parent
    assert not aperture_1.outdoor_shades[0].is_indoor
    assert len(aperture_2.outdoor_shades) == 0


def test_aperture_extruded_border():
    """Test the creation of an extruded border for Aperture objects."""
    pts_1 = (Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 0, 0))
    pts_2 = (Point3D(0, 0, 0), Point3D(2, 0, 3), Point3D(4, 0, 3))
    aperture_1 = Aperture('RectangleWindow', Face3D(pts_1))
    aperture_2 = Aperture('TriangleWindow', Face3D(pts_2))

    aperture_1.extruded_border(0.1)
    aperture_2.extruded_border(0.1)
    aperture_1.extruded_border(0.1, True)
    aperture_2.extruded_border(0.1, True)

    assert len(aperture_1.shades) == 8
    assert aperture_1.outdoor_shades[0].center.y > 0
    assert aperture_1.outdoor_shades[0].has_parent
    assert all(not shd.is_indoor for shd in aperture_1.outdoor_shades)
    assert all(shd.is_indoor for shd in aperture_1.indoor_shades)
    assert len(aperture_2.shades) == 6
    assert aperture_2.outdoor_shades[0].center.y > 0
    assert aperture_1.indoor_shades[0].center.y < 0
    assert aperture_2.indoor_shades[0].center.y < 0
    assert all(not shd.is_indoor for shd in aperture_2.outdoor_shades)
    assert all(shd.is_indoor for shd in aperture_2.indoor_shades)


def test_aperture_louvers_by_count():
    """Test the creation of a louvers_by_count for Face objects."""
    pts_1 = (Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 0, 0))
    aperture = Aperture('RectangleWindow', Face3D(pts_1))
    aperture.louvers_by_count(3, 0.2, 0.1, 5)

    assert len(aperture.outdoor_shades) == 3
    for louver in aperture.outdoor_shades:
        assert isinstance(louver, Shade)
        assert louver.area == 5 * 0.2
        assert louver.has_parent


def test_aperture_louvers_by_distance_between():
    """Test the creation of a louvers_by_distance_between for Aperture objects."""
    pts_1 = (Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(5, 0, 3), Point3D(5, 0, 0))
    aperture = Aperture('RectangleWindow', Face3D(pts_1))
    aperture.louvers_by_distance_between(0.5, 0.2, 0.1)
    assert len(aperture.outdoor_shades) == 6
    for louver in aperture.outdoor_shades:
        assert isinstance(louver, Shade)
        assert louver.area == 5 * 0.2
        assert louver.has_parent

    aperture.remove_shades()
    aperture.louvers_by_distance_between(0.5, 0.2, 0.1, max_count=3)
    assert len(aperture.outdoor_shades) == 3
    for louver in aperture.outdoor_shades:
        assert isinstance(louver, Shade)
        assert louver.area == 5 * 0.2
        assert louver.has_parent

    aperture.remove_shades()
    aperture.louvers_by_distance_between(0.5, 0.2, 0.1, max_count=10)
    assert len(aperture.outdoor_shades) == 6


def test_move():
    """Test the Aperture move method."""
    pts_1 = (Point3D(0, 0, 0), Point3D(2, 0, 0), Point3D(2, 2, 0), Point3D(0, 2, 0))
    plane_1 = Plane(Vector3D(0, 0, 1), Point3D(0, 0, 0))
    aperture = Aperture('RectangleWindow', Face3D(pts_1, plane_1))

    vec_1 = Vector3D(2, 2, 2)
    new_ap = aperture.duplicate()
    new_ap.move(vec_1)
    assert new_ap.geometry[0] == Point3D(2, 2, 2)
    assert new_ap.geometry[1] == Point3D(4, 2, 2)
    assert new_ap.geometry[2] == Point3D(4, 4, 2)
    assert new_ap.geometry[3] == Point3D(2, 4, 2)
    assert new_ap.normal == aperture.normal
    assert aperture.area == new_ap.area
    assert aperture.perimeter == new_ap.perimeter


def test_scale():
    """Test the Aperture scale method."""
    pts = (Point3D(1, 1, 2), Point3D(2, 1, 2), Point3D(2, 2, 2), Point3D(1, 2, 2))
    plane = Plane(Vector3D(0, 0, 1), Point3D(0, 0, 2))
    aperture = Aperture('RectangleWindow', Face3D(pts, plane))

    new_ap = aperture.duplicate()
    new_ap.scale(2)
    assert new_ap.geometry[0] == Point3D(2, 2, 4)
    assert new_ap.geometry[1] == Point3D(4, 2, 4)
    assert new_ap.geometry[2] == Point3D(4, 4, 4)
    assert new_ap.geometry[3] == Point3D(2, 4, 4)
    assert new_ap.area == aperture.area * 2 ** 2
    assert new_ap.perimeter == aperture.perimeter * 2
    assert new_ap.normal == aperture.normal


def test_rotate():
    """Test the Aperture rotate method."""
    pts = (Point3D(0, 0, 2), Point3D(2, 0, 2), Point3D(2, 2, 2), Point3D(0, 2, 2))
    plane = Plane(Vector3D(0, 0, 1), Point3D(0, 0, 2))
    aperture = Aperture('RectangleWindow', Face3D(pts, plane))
    origin = Point3D(0, 0, 0)
    axis = Vector3D(1, 0, 0)

    test_1 = aperture.duplicate()
    test_1.rotate(axis, 180, origin)
    assert test_1.geometry[0].x == pytest.approx(0, rel=1e-3)
    assert test_1.geometry[0].y == pytest.approx(0, rel=1e-3)
    assert test_1.geometry[0].z == pytest.approx(-2, rel=1e-3)
    assert test_1.geometry[2].x == pytest.approx(2, rel=1e-3)
    assert test_1.geometry[2].y == pytest.approx(-2, rel=1e-3)
    assert test_1.geometry[2].z == pytest.approx(-2, rel=1e-3)
    assert aperture.area == test_1.area
    assert len(aperture.vertices) == len(test_1.vertices)

    test_2 = aperture.duplicate()
    test_2.rotate(axis, 90, origin)
    assert test_2.geometry[0].x == pytest.approx(0, rel=1e-3)
    assert test_2.geometry[0].y == pytest.approx(-2, rel=1e-3)
    assert test_2.geometry[0].z == pytest.approx(0, rel=1e-3)
    assert test_2.geometry[2].x == pytest.approx(2, rel=1e-3)
    assert test_2.geometry[2].y == pytest.approx(-2, rel=1e-3)
    assert test_2.geometry[2].z == pytest.approx(2, rel=1e-3)
    assert aperture.area == test_2.area
    assert len(aperture.vertices) == len(test_2.vertices)


def test_rotate_xy():
    """Test the Aperture rotate_xy method."""
    pts = (Point3D(1, 1, 2), Point3D(2, 1, 2), Point3D(2, 2, 2), Point3D(1, 2, 2))
    plane = Plane(Vector3D(0, 0, 1), Point3D(0, 0, 2))
    aperture = Aperture('RectangleWindow', Face3D(pts, plane))
    origin_1 = Point3D(1, 1, 0)

    test_1 = aperture.duplicate()
    test_1.rotate_xy(180, origin_1)
    assert test_1.geometry[0].x == pytest.approx(1, rel=1e-3)
    assert test_1.geometry[0].y == pytest.approx(1, rel=1e-3)
    assert test_1.geometry[0].z == pytest.approx(2, rel=1e-3)
    assert test_1.geometry[2].x == pytest.approx(0, rel=1e-3)
    assert test_1.geometry[2].y == pytest.approx(0, rel=1e-3)
    assert test_1.geometry[2].z == pytest.approx(2, rel=1e-3)

    test_2 = aperture.duplicate()
    test_2.rotate_xy(90, origin_1)
    assert test_2.geometry[0].x == pytest.approx(1, rel=1e-3)
    assert test_2.geometry[0].y == pytest.approx(1, rel=1e-3)
    assert test_1.geometry[0].z == pytest.approx(2, rel=1e-3)
    assert test_2.geometry[2].x == pytest.approx(0, rel=1e-3)
    assert test_2.geometry[2].y == pytest.approx(2, rel=1e-3)
    assert test_1.geometry[2].z == pytest.approx(2, rel=1e-3)


def test_reflect():
    """Test the Aperture reflect method."""
    pts = (Point3D(1, 1, 2), Point3D(2, 1, 2), Point3D(2, 2, 2), Point3D(1, 2, 2))
    plane = Plane(Vector3D(0, 0, 1), Point3D(0, 0, 2))
    aperture = Aperture('RectangleWindow', Face3D(pts, plane))

    origin_1 = Point3D(1, 0, 2)
    origin_2 = Point3D(0, 0, 2)
    normal_1 = Vector3D(1, 0, 0)
    normal_2 = Vector3D(-1, -1, 0).normalize()
    plane_1 = Plane(normal_1, origin_1)
    plane_2 = Plane(normal_2, origin_2)
    plane_3 = Plane(normal_2, origin_1)

    test_1 = aperture.duplicate()
    test_1.reflect(plane_1)
    assert test_1.geometry[-1].x == pytest.approx(1, rel=1e-3)
    assert test_1.geometry[-1].y == pytest.approx(1, rel=1e-3)
    assert test_1.geometry[-1].z == pytest.approx(2, rel=1e-3)
    assert test_1.geometry[1].x == pytest.approx(0, rel=1e-3)
    assert test_1.geometry[1].y == pytest.approx(2, rel=1e-3)
    assert test_1.geometry[1].z == pytest.approx(2, rel=1e-3)

    test_1 = aperture.duplicate()
    test_1.reflect(plane_2)
    assert test_1.geometry[-1].x == pytest.approx(-1, rel=1e-3)
    assert test_1.geometry[-1].y == pytest.approx(-1, rel=1e-3)
    assert test_1.geometry[-1].z == pytest.approx(2, rel=1e-3)
    assert test_1.geometry[1].x == pytest.approx(-2, rel=1e-3)
    assert test_1.geometry[1].y == pytest.approx(-2, rel=1e-3)
    assert test_1.geometry[1].z == pytest.approx(2, rel=1e-3)

    test_2 = aperture.duplicate()
    test_2.reflect(plane_3)
    assert test_2.geometry[-1].x == pytest.approx(0, rel=1e-3)
    assert test_2.geometry[-1].y == pytest.approx(0, rel=1e-3)
    assert test_2.geometry[-1].z == pytest.approx(2, rel=1e-3)
    assert test_2.geometry[1].x == pytest.approx(-1, rel=1e-3)
    assert test_2.geometry[1].y == pytest.approx(-1, rel=1e-3)
    assert test_2.geometry[1].z == pytest.approx(2, rel=1e-3)


def test_remove_colinear_vertices():
    """Test the remove_colinear_vertices method."""
    pts_1 = (Point3D(0, 0), Point3D(2, 0), Point3D(2, 2), Point3D(0, 2))
    pts_2 = (Point3D(0, 0), Point3D(1, 0), Point3D(2, 0), Point3D(2, 2),
             Point3D(0, 2))
    ap_1 = Aperture('TestAperture1', Face3D(pts_1))
    ap_2 = Aperture('TestAperture1', Face3D(pts_2))

    assert len(ap_1.geometry.vertices) == 4
    assert len(ap_2.geometry.vertices) == 5
    ap_1.remove_colinear_vertices(0.0001)
    ap_2.remove_colinear_vertices(0.0001)
    assert len(ap_1.geometry.vertices) == 4
    assert len(ap_2.geometry.vertices) == 4


def test_check_planar():
    """Test the check_planar method."""
    pts_1 = (Point3D(0, 0, 2), Point3D(2, 0, 2), Point3D(2, 2, 2), Point3D(0, 2, 2))
    pts_2 = (Point3D(0, 0, 0), Point3D(2, 0, 2), Point3D(2, 2, 2), Point3D(0, 2, 2))
    pts_3 = (Point3D(0, 0, 2.0001), Point3D(2, 0, 2), Point3D(2, 2, 2), Point3D(0, 2, 2))
    plane_1 = Plane(Vector3D(0, 0, 1), Point3D(0, 0, 2))
    aperture_1 = Aperture('Window1', Face3D(pts_1, plane_1))
    aperture_2 = Aperture('Window2', Face3D(pts_2, plane_1))
    aperture_3 = Aperture('Window3', Face3D(pts_3, plane_1))

    assert aperture_1.check_planar(0.001) == ''
    assert aperture_2.check_planar(0.001, False) != ''
    with pytest.raises(Exception):
        aperture_2.check_planar(0.0001)
    assert aperture_3.check_planar(0.001) == ''
    assert aperture_3.check_planar(0.000001, False) != ''
    with pytest.raises(Exception):
        aperture_3.check_planar(0.000001)


def test_check_self_intersecting():
    """Test the check_self_intersecting method."""
    plane_1 = Plane(Vector3D(0, 0, 1))
    plane_2 = Plane(Vector3D(0, 0, -1))
    pts_1 = (Point3D(0, 0), Point3D(2, 0), Point3D(2, 2), Point3D(0, 2))
    pts_2 = (Point3D(0, 0), Point3D(0, 2), Point3D(2, 0), Point3D(2, 2))
    aperture_1 = Aperture('Window1', Face3D(pts_1, plane_1))
    aperture_2 = Aperture('Window2', Face3D(pts_2, plane_1))
    aperture_3 = Aperture('Window3', Face3D(pts_1, plane_2))
    aperture_4 = Aperture('Window4', Face3D(pts_2, plane_2))

    assert aperture_1.check_self_intersecting(0.01, False) == ''
    assert aperture_2.check_self_intersecting(0.01, False) != ''
    with pytest.raises(Exception):
        assert aperture_2.check_self_intersecting(0.01, True)
    assert aperture_3.check_self_intersecting(0.01, False) == ''
    assert aperture_4.check_self_intersecting(0.01, False) != ''
    with pytest.raises(Exception):
        assert aperture_4.check_self_intersecting(0.01, True)


def test_check_non_zero():
    """Test the check_non_zero method."""
    plane_1 = Plane(Vector3D(0, 0, 1))
    pts_1 = (Point3D(0, 0), Point3D(2, 0), Point3D(2, 2))
    pts_2 = (Point3D(0, 0), Point3D(2, 0), Point3D(2, 0))
    aperture_1 = Aperture('Window1', Face3D(pts_1, plane_1))
    aperture_2 = Aperture('Window2', Face3D(pts_2, plane_1))

    assert aperture_1.check_non_zero(0.0001, False) == ''
    assert aperture_2.check_non_zero(0.0001, False) != ''
    with pytest.raises(Exception):
        assert aperture_2.check_non_zero(0.0001, True)


def test_to_dict():
    """Test the Aperture to_dict method."""
    vertices = [[0, 0, 0], [0, 10, 0], [0, 10, 3], [0, 0, 3]]
    unique_id = str(py_uuid.uuid4())
    ap = Aperture.from_vertices(unique_id, vertices)
    ap.display_name = 'Rectangle Window'

    ad = ap.to_dict()
    assert ad['type'] == 'Aperture'
    assert ad['identifier'] == unique_id
    assert ad['display_name'] == 'Rectangle Window'
    assert 'geometry' in ad
    assert len(ad['geometry']['boundary']) == len(vertices)
    assert 'properties' in ad
    assert ad['properties']['type'] == 'ApertureProperties'
    assert not ad['is_operable']
    assert ad['boundary_condition']['type'] == 'Outdoors'


def test_to_from_dict():
    """Test the to/from dict of Aperture objects."""
    vertices = [[0, 0, 0], [0, 10, 0], [0, 10, 3], [0, 0, 3]]
    ap = Aperture.from_vertices('RectangleWindow', vertices)

    ap_dict = ap.to_dict()
    new_ap = Aperture.from_dict(ap_dict)
    assert isinstance(new_ap, Aperture)
    assert new_ap.to_dict() == ap_dict


def test_writer():
    """Test the Aperture writer object."""
    vertices = [[0, 0, 0], [0, 10, 0], [0, 10, 3], [0, 0, 3]]
    ap = Aperture.from_vertices('RectangleWindow', vertices)

    writers = [mod for mod in dir(ap.to) if not mod.startswith('_')]
    for writer in writers:
        assert callable(getattr(ap.to, writer))
