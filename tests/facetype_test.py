"""test Face class."""
from honeybee.facetype import Wall, RoofCeiling, Floor, AirBoundary, face_types

import pytest


def test_wall():
    """Test the initialization of the Wall face type."""
    wall_type_1 = Wall()
    wall_type_2 = face_types.wall

    str(wall_type_1)  # test the string representation
    assert wall_type_1 == wall_type_2
    assert wall_type_1 != face_types.floor


def test_roof_ceiling():
    """Test the initialization of the RoofCeiling face type."""
    roof_type_1 = RoofCeiling()
    roof_type_2 = face_types.roof_ceiling

    str(roof_type_1)  # test the string representation
    assert roof_type_1 == roof_type_2
    assert roof_type_1 != face_types.floor


def test_floor():
    """Test the initialization of the Floor face type."""
    floor_type_1 = Floor()
    floor_type_2 = face_types.floor

    str(floor_type_1)  # test the string representation
    assert floor_type_1 == floor_type_2
    assert floor_type_1 != face_types.wall


def test_air_boundary():
    """Test the initialization of the AirBoundary face type."""
    air_type_1 = AirBoundary()
    air_type_2 = face_types.air_boundary

    str(air_type_1)  # test the string representation
    assert air_type_1 == air_type_2
    assert air_type_1 != face_types.wall


def test_face_type_by_name():
    """Test the face type by_name method."""
    assert isinstance(face_types.by_name('Wall'), Wall)
    assert isinstance(face_types.by_name('wall'), Wall)
    assert isinstance(face_types.by_name('WALL'), Wall)

    assert isinstance(face_types.by_name('AirBoundary'), AirBoundary)
    assert isinstance(face_types.by_name('air_boundary'), AirBoundary)
    assert isinstance(face_types.by_name('AirBoundary'), AirBoundary)

    with pytest.raises(ValueError):
        face_types.by_name('Not_a_face_type')
    with pytest.raises(ValueError):
        face_types.by_name('walls')
