"""Test the ShadeMesh class."""
from honeybee.shademesh import ShadeMesh

from ladybug_geometry.geometry3d import Point3D, Vector3D, Plane, Mesh3D

import pytest


def test_shade_mesh_init():
    """Test the initialization of ShadeMesh objects."""
    pts = (Point3D(0, 0, 4), Point3D(0, 2, 4), Point3D(2, 2, 4),
           Point3D(2, 0, 4), Point3D(4, 0, 4))
    mesh = Mesh3D(pts, [(0, 1, 2, 3), (2, 3, 4)])
    shade = ShadeMesh('Awning_1', mesh)
    str(shade)  # test the string representation

    assert shade.identifier == 'Awning_1'
    assert shade.display_name == 'Awning_1'
    assert isinstance(shade.geometry, Mesh3D)
    assert len(shade.vertices) == 5
    assert len(shade.faces) == 2
    assert shade.center == Point3D(2, 1, 4)
    assert shade.area == 6
    assert isinstance(shade.min, Point3D)
    assert isinstance(shade.max, Point3D)
    assert shade.is_detached


def test_shade_duplicate():
    """Test the duplication of shade objects."""
    pts = (Point3D(0, 0, 4), Point3D(0, 2, 4), Point3D(2, 2, 4),
           Point3D(2, 0, 4), Point3D(4, 0, 4))
    mesh = Mesh3D(pts, [(0, 1, 2, 3), (2, 3, 4)])
    shd_1 = ShadeMesh('Awning_1', mesh)
    shd_2 = shd_1.duplicate()

    assert shd_1 is not shd_2
    for i, pt in enumerate(shd_1.vertices):
        assert pt == shd_2.vertices[i]
    assert shd_1.identifier == shd_2.identifier
    assert shd_1.is_detached == shd_2.is_detached

    shd_2.move(Vector3D(0, 1, 0))
    for i, pt in enumerate(shd_1.vertices):
        assert pt != shd_2.vertices[i]


def test_move():
    """Test the ShadeMesh move method."""
    pts_1 = (Point3D(0, 0, 0), Point3D(2, 0, 0), Point3D(2, 2, 0), Point3D(0, 2, 0))
    mesh = Mesh3D(pts_1, [(0, 1, 2), (2, 3, 0)])
    shade = ShadeMesh('Awning_1', mesh)

    vec_1 = Vector3D(2, 2, 2)
    new_shd = shade.duplicate()
    new_shd.move(vec_1)
    assert new_shd.geometry[0] == Point3D(2, 2, 2)
    assert new_shd.geometry[1] == Point3D(4, 2, 2)
    assert new_shd.geometry[2] == Point3D(4, 4, 2)
    assert new_shd.geometry[3] == Point3D(2, 4, 2)
    assert shade.area == new_shd.area


def test_scale():
    """Test the shade scale method."""
    pts = (Point3D(1, 1, 2), Point3D(2, 1, 2), Point3D(2, 2, 2), Point3D(1, 2, 2))
    mesh = Mesh3D(pts, [(0, 1, 2), (2, 3, 0)])
    shade = ShadeMesh('Awning_1', mesh)

    new_shd = shade.duplicate()
    new_shd.scale(2)
    assert new_shd.geometry[0] == Point3D(2, 2, 4)
    assert new_shd.geometry[1] == Point3D(4, 2, 4)
    assert new_shd.geometry[2] == Point3D(4, 4, 4)
    assert new_shd.geometry[3] == Point3D(2, 4, 4)
    assert new_shd.area == shade.area * 2 ** 2


def test_rotate():
    """Test the shade rotate method."""
    pts = (Point3D(0, 0, 2), Point3D(2, 0, 2), Point3D(2, 2, 2), Point3D(0, 2, 2))
    mesh = Mesh3D(pts, [(0, 1, 2), (2, 3, 0)])
    shade = ShadeMesh('Awning_1', mesh)
    origin = Point3D(0, 0, 0)
    axis = Vector3D(1, 0, 0)

    test_1 = shade.duplicate()
    test_1.rotate(axis, 180, origin)
    assert test_1.geometry[0].x == pytest.approx(0, rel=1e-3)
    assert test_1.geometry[0].y == pytest.approx(0, rel=1e-3)
    assert test_1.geometry[0].z == pytest.approx(-2, rel=1e-3)
    assert test_1.geometry[2].x == pytest.approx(2, rel=1e-3)
    assert test_1.geometry[2].y == pytest.approx(-2, rel=1e-3)
    assert test_1.geometry[2].z == pytest.approx(-2, rel=1e-3)
    assert shade.area == test_1.area
    assert len(shade.vertices) == len(test_1.vertices)

    test_2 = shade.duplicate()
    test_2.rotate(axis, 90, origin)
    assert test_2.geometry[0].x == pytest.approx(0, rel=1e-3)
    assert test_2.geometry[0].y == pytest.approx(-2, rel=1e-3)
    assert test_2.geometry[0].z == pytest.approx(0, rel=1e-3)
    assert test_2.geometry[2].x == pytest.approx(2, rel=1e-3)
    assert test_2.geometry[2].y == pytest.approx(-2, rel=1e-3)
    assert test_2.geometry[2].z == pytest.approx(2, rel=1e-3)
    assert shade.area == test_2.area
    assert len(shade.vertices) == len(test_2.vertices)


def test_rotate_xy():
    """Test the Shade rotate_xy method."""
    pts = (Point3D(1, 1, 2), Point3D(2, 1, 2), Point3D(2, 2, 2), Point3D(1, 2, 2))
    mesh = Mesh3D(pts, [(0, 1, 2), (2, 3, 0)])
    shade = ShadeMesh('Awning_1', mesh)
    origin_1 = Point3D(1, 1, 0)

    test_1 = shade.duplicate()
    test_1.rotate_xy(180, origin_1)
    assert test_1.geometry[0].x == pytest.approx(1, rel=1e-3)
    assert test_1.geometry[0].y == pytest.approx(1, rel=1e-3)
    assert test_1.geometry[0].z == pytest.approx(2, rel=1e-3)
    assert test_1.geometry[2].x == pytest.approx(0, rel=1e-3)
    assert test_1.geometry[2].y == pytest.approx(0, rel=1e-3)
    assert test_1.geometry[2].z == pytest.approx(2, rel=1e-3)

    test_2 = shade.duplicate()
    test_2.rotate_xy(90, origin_1)
    assert test_2.geometry[0].x == pytest.approx(1, rel=1e-3)
    assert test_2.geometry[0].y == pytest.approx(1, rel=1e-3)
    assert test_1.geometry[0].z == pytest.approx(2, rel=1e-3)
    assert test_2.geometry[2].x == pytest.approx(0, rel=1e-3)
    assert test_2.geometry[2].y == pytest.approx(2, rel=1e-3)
    assert test_1.geometry[2].z == pytest.approx(2, rel=1e-3)


def test_reflect():
    """Test the Shade reflect method."""
    pts = (Point3D(1, 1, 2), Point3D(2, 1, 2), Point3D(2, 2, 2), Point3D(1, 2, 2))
    mesh = Mesh3D(pts, [(0, 1, 2), (2, 3, 0)])
    shade = ShadeMesh('Awning_1', mesh)

    origin_1 = Point3D(1, 0, 2)
    origin_2 = Point3D(0, 0, 2)
    normal_1 = Vector3D(1, 0, 0)
    normal_2 = Vector3D(-1, -1, 0).normalize()
    plane_1 = Plane(normal_1, origin_1)
    plane_2 = Plane(normal_2, origin_2)
    plane_3 = Plane(normal_2, origin_1)

    test_1 = shade.duplicate()
    test_1.reflect(plane_1)
    assert test_1.geometry[0].x == pytest.approx(1, rel=1e-3)
    assert test_1.geometry[0].y == pytest.approx(1, rel=1e-3)
    assert test_1.geometry[0].z == pytest.approx(2, rel=1e-3)
    assert test_1.geometry[2].x == pytest.approx(0, rel=1e-3)
    assert test_1.geometry[2].y == pytest.approx(2, rel=1e-3)
    assert test_1.geometry[2].z == pytest.approx(2, rel=1e-3)

    test_1 = shade.duplicate()
    test_1.reflect(plane_2)
    assert test_1.geometry[0].x == pytest.approx(-1, rel=1e-3)
    assert test_1.geometry[0].y == pytest.approx(-1, rel=1e-3)
    assert test_1.geometry[0].z == pytest.approx(2, rel=1e-3)
    assert test_1.geometry[2].x == pytest.approx(-2, rel=1e-3)
    assert test_1.geometry[2].y == pytest.approx(-2, rel=1e-3)
    assert test_1.geometry[2].z == pytest.approx(2, rel=1e-3)

    test_2 = shade.duplicate()
    test_2.reflect(plane_3)
    assert test_2.geometry[0].x == pytest.approx(0, rel=1e-3)
    assert test_2.geometry[0].y == pytest.approx(0, rel=1e-3)
    assert test_2.geometry[0].z == pytest.approx(2, rel=1e-3)
    assert test_2.geometry[2].x == pytest.approx(-1, rel=1e-3)
    assert test_2.geometry[2].y == pytest.approx(-1, rel=1e-3)
    assert test_2.geometry[2].z == pytest.approx(2, rel=1e-3)


def test_triangulate_and_remove_degenerate_faces():
    """Test the triangulate_and_remove_degenerate_faces method."""
    pts = (Point3D(0, 0, 4), Point3D(0, 2, 4), Point3D(2, 2, 4),
           Point3D(2, 0, 4), Point3D(4, 0, 4))
    mesh = Mesh3D(pts, [(0, 1, 2, 3), (2, 3, 4)])
    shade = ShadeMesh('Awning_1', mesh)
    shade.triangulate_and_remove_degenerate_faces(0.01)
    assert len(shade.faces) == 2
    assert len(shade.faces[0]) == 4
    assert len(shade.faces[1]) == 3

    pts = (Point3D(0, 0, 2), Point3D(0, 2, 4), Point3D(2, 2, 4),
           Point3D(2, 0, 4), Point3D(4, 0, 4))
    mesh = Mesh3D(pts, [(0, 1, 2, 3), (2, 3, 4)])
    shade = ShadeMesh('Awning_1', mesh)
    shade.triangulate_and_remove_degenerate_faces(0.01)
    assert len(shade.faces) == 3
    assert len(shade.faces[0]) == 3
    assert len(shade.faces[1]) == 3

    pts = (Point3D(0, 2, 4), Point3D(0, 2, 4), Point3D(2, 2, 4),
           Point3D(2, 0, 4), Point3D(4, 0, 4))
    mesh = Mesh3D(pts, [(0, 1, 2, 3), (2, 3, 4)])
    shade = ShadeMesh('Awning_1', mesh)
    shade.triangulate_and_remove_degenerate_faces(0.01)
    assert len(shade.faces) == 2
    assert len(shade.faces[0]) == 3
    assert len(shade.faces[1]) == 3

    pts = (Point3D(0, 0, 4), Point3D(0, 2, 4), Point3D(2, 2, 4),
           Point3D(2, 0, 4), Point3D(2, 0, 4))
    mesh = Mesh3D(pts, [(0, 1, 2, 3), (2, 3, 4)])
    shade = ShadeMesh('Awning_1', mesh)
    shade.triangulate_and_remove_degenerate_faces(0.01)
    assert len(shade.faces) == 1
    assert len(shade.faces[0]) == 4

    pts = (Point3D(1, 1, 4), Point3D(0, 2, 4), Point3D(2, 2, 4),
           Point3D(2, 0, 4), Point3D(4, 0, 4))
    mesh = Mesh3D(pts, [(0, 1, 2, 3), (2, 3, 4)])
    shade = ShadeMesh('Awning_1', mesh)
    shade.triangulate_and_remove_degenerate_faces(0.01)
    assert len(shade.faces) == 2
    assert len(shade.faces[0]) == 3
    assert len(shade.faces[1]) == 3


def test_to_dict():
    """Test the shade to_dict method."""
    pts = (Point3D(0, 0, 4), Point3D(0, 2, 4), Point3D(2, 2, 4),
           Point3D(2, 0, 4), Point3D(4, 0, 4))
    mesh = Mesh3D(pts, [(0, 1, 2, 3), (2, 3, 4)])
    shd = ShadeMesh('Awning_1', mesh)

    shd = shd.to_dict()
    assert shd['type'] == 'ShadeMesh'
    assert shd['identifier'] == 'Awning_1'
    assert shd['display_name'] == 'Awning_1'
    assert 'geometry' in shd
    assert len(shd['geometry']['vertices']) == len(pts)
    assert 'properties' in shd
    assert shd['properties']['type'] == 'ShadeMeshProperties'


def test_to_from_dict():
    """Test the to/from dict of Shade objects."""
    pts = (Point3D(0, 0, 4), Point3D(0, 2, 4), Point3D(2, 2, 4),
           Point3D(2, 0, 4), Point3D(4, 0, 4))
    mesh = Mesh3D(pts, [(0, 1, 2, 3), (2, 3, 4)])
    shd = ShadeMesh('Awning_1', mesh)

    shd_dict = shd.to_dict()
    new_shd = ShadeMesh.from_dict(shd_dict)
    assert isinstance(new_shd, ShadeMesh)
    assert new_shd.to_dict() == shd_dict


def test_writer():
    """Test the Shade writer object."""
    pts = (Point3D(0, 0, 4), Point3D(0, 2, 4), Point3D(2, 2, 4),
           Point3D(2, 0, 4), Point3D(4, 0, 4))
    mesh = Mesh3D(pts, [(0, 1, 2, 3), (2, 3, 4)])
    shd = ShadeMesh('Awning_1', mesh)

    writers = [mod for mod in dir(shd.to) if not mod.startswith('_')]
    for writer in writers:
        assert callable(getattr(shd.to, writer))
