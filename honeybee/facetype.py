"""Energy Types."""
from ladybug_geometry.geometry3d.pointvector import Vector3D
import math


class _FaceType(object):
    @property
    def name(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.name


class Wall(_FaceType):
    pass


class RoofCeiling(_FaceType):
    pass


class Floor(_FaceType):
    pass


class AirWall(_FaceType):
    pass


class Shading(_FaceType):
    pass


class _Types(object):
    """Face types."""

    def __init__(self):
        self._wall = Wall()
        self._roof_ceiling = RoofCeiling()
        self._floor = Floor()
        self._air_wall = AirWall()
        self._shading = Shading()

    @property
    def wall(self):
        return self._wall

    @property
    def roof_ceiling(self):
        return self._roof_ceiling

    @property
    def floor(self):
        return self._floor

    @property
    def airwall(self):
        return self._air_wall

    @property
    def shading(self):
        return self._shading

    def __contains__(self, value):
        return isinstance(value, _FaceType)


face_types = _Types()


def get_type_from_normal(normal_vector, roof_angle=30, floor_angle=150):
    """Return face type based on the angle between Z axis and normal vector.

    Angles between 0 and roof_angle will be set to roof_ceiling.
    Angles between roof_angle and floor_angle will be set to wall.
    Angles larger than floor angle will be set to floor.

    args:
        normal_vector: Normal vector as a ladybug Vector3D.
        roof_angle: Cutting angle for roof from Z axis (default: 30).
        floor_angle: Cutting angle for floor from Z axis (default: 150).
    
    returns:
        face type.
    """

    roof_angle = math.radians(roof_angle)
    floor_angle = math.radians(floor_angle)
    z_axis = Vector3D(0, 0, 1)
    angle = z_axis.angle(normal_vector)
    if angle < roof_angle:
        return face_types.roof_ceiling
    elif roof_angle <= angle < floor_angle:
        return face_types.wall
    else:
        return face_types.floor

    return face_types.wall
