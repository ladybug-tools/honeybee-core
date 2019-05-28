"""test Face class."""
from honeybee.face import Face
from honeybee.properties import face_types as Types
import pytest


def test_name():
    vertices = [[0, 0, 0], [0, 10, 0], [0, 10, 3], [0, 0, 3]]
    f = Face.from_vertices('Wall: SIM_INT_AIR [920980]', vertices)
    assert f.name == 'WallSIM_INT_AIR920980'
    assert f.name_original == 'Wall: SIM_INT_AIR [920980]'


def test_vertices_count():
    with pytest.raises(Exception):
        Face.from_vertices('no vertices', [], Types.wall)


def test_type_from_vertices():
    vertices_wall = [[0, 0, 0], [0, 10, 0], [0, 10, 3], [0, 0, 3]]
    vertices_floor = [[0, 0, 0], [0, 10, 0], [10, 10, 0], [10, 0, 0]]
    vertices_roof = list(reversed(vertices_floor))

    wf = Face.from_vertices('wall', vertices_wall)
    assert wf.properties.face_type == wf.properties.TYPES.wall

    rf = Face.from_vertices('roof', vertices_roof)
    assert rf.properties.face_type == rf.properties.TYPES.roof_ceiling

    ff = Face.from_vertices('floor', vertices_floor)
    assert ff.properties.face_type == ff.properties.TYPES.floor
