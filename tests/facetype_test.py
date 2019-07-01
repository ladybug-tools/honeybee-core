"""test Face class."""
from honeybee.facetype import Wall, RoofCeiling, Floor, AirWall, face_types

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


def test_air_wall():
    """Test the initialization of the AirWall face type."""
    air_type_1 = AirWall()
    air_type_2 = face_types.air_wall

    str(air_type_1)  # test the string representation
    assert air_type_1 == air_type_2
    assert air_type_1 != face_types.wall
