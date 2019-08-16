"""Face Types."""
from ladybug_geometry.geometry3d.pointvector import Vector3D
import re
import math


class _FaceType(object):
    __slots__ = ()

    def __init__(self):
        pass

    @property
    def name(self):
        return self.__class__.__name__

    def ToString(self):
        return self.__repr__()

    def __eq__(self, other):
        return self.__class__ == other.__class__

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return self.name


class Wall(_FaceType):
    """Type for walls."""
    __slots__ = ()
    pass


class RoofCeiling(_FaceType):
    """Type for roofs and ceilings."""
    __slots__ = ()
    pass


class Floor(_FaceType):
    """Type for floors."""
    __slots__ = ()
    pass


class AirWall(_FaceType):
    """Type for virtual partitions between Rooms.

    Note that the use of the word 'Wall' in AirWall does not limit the application
    of this type to vertical faces. It can be applied to any face between two Rooms.
    """
    __slots__ = ()
    pass


class _FaceTypes(object):
    """Face types."""

    def __init__(self):
        self._wall = Wall()
        self._roof_ceiling = RoofCeiling()
        self._floor = Floor()
        self._air_wall = AirWall()

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
    def air_wall(self):
        return self._air_wall

    def by_name(self, face_type_name):
        """Get a Face Type instance from its name.

        Args:
            face_type_name: A text string for the face type (eg. "Wall").
        """
        attr_name = re.sub('(?<!^)(?=[A-Z])', '_', face_type_name).lower()
        try:
            return getattr(self, attr_name)
        except AttributeError:
            raise AttributeError(
                'Face Type "{}" is not supported.'.format(face_type_name))

    def __contains__(self, value):
        return isinstance(value, _FaceType)

    def __repr__(self):
        return 'Face Types:\nWall\nRoofCeiling\nFloor\nAirWall'


face_types = _FaceTypes()


def get_type_from_normal(normal_vector, roof_angle=30, floor_angle=150):
    """Return face type based on the angle between Z axis and normal vector.

    Angles between 0 and roof_angle will be set to roof_ceiling.
    Angles between roof_angle and floor_angle will be set to wall.
    Angles larger than floor angle will be set to floor.

    args:
        normal_vector: Normal vector as a ladybug_geometry Vector3D.
        roof_angle: Cutting angle for roof from Z axis in degrees (default: 30).
        floor_angle: Cutting angle for floor from Z axis in degrees (default: 150).

    Returns:
        Face type instance.
    """
    z_axis = Vector3D(0, 0, 1)
    angle = math.degrees(z_axis.angle(normal_vector))
    if angle < roof_angle:
        return face_types.roof_ceiling
    elif roof_angle <= angle < floor_angle:
        return face_types.wall
    else:
        return face_types.floor

    return face_types.wall
