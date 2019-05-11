"""test Face class."""
from honeybee.face import Face
from honeybee.properties import Types
import pytest


def test_name():
    vertices = [[0, 0, 0], [0, 10, 0], [0, 10, 3], [0, 0, 3]]
    f = Face('Wall: SIM_INT_AIR [920980]', vertices)
    assert f.name == 'WallSIM_INT_AIR920980'
    assert f.name_original == 'Wall: SIM_INT_AIR [920980]'


def test_vertices_count():
    # fails
    with pytest.raises(Exception):
        Face('no vertices', [])


def test_vertices_duplicate():
    # fails
    vertices = [[0, 0, 0], [0, 10, 0], [0, 10, 0]]
    with pytest.raises(Exception):
        Face('duplicate vertices', vertices)


def test_type_from_vertices():
    # fails
    vertices_wall = [[0, 0, 0], [0, 10, 0], [0, 10, 3], [0, 0, 3]]
    vertices_roof = [[0, 0, 0], [0, 10, 0], [10, 10, 0], [10, 0, 0]]
    vertices_floor = list(reversed(vertices_roof))

    wf = Face('wall', vertices_wall)
    assert wf.properties.face_type == wf.properties.TYPES.wall

    rf = Face('roof', vertices_roof)
    assert rf.properties.face_type == rf.properties.TYPES.roof_ceiling

    ff = Face('floor', vertices_floor)
    assert ff.properties.face_type == ff.properties.TYPES.floor
