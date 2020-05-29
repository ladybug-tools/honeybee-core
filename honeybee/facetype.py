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


class AirBoundary(_FaceType):
    """Type for air boundaries (aka. virtual partitions) between Rooms."""
    __slots__ = ()
    pass


class _FaceTypes(object):
    """Face types."""

    def __init__(self):
        self._wall = Wall()
        self._roof_ceiling = RoofCeiling()
        self._floor = Floor()
        self._air_boundary = AirBoundary()
        self._type_name_dict = None

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
    def air_boundary(self):
        return self._air_boundary

    def by_name(self, face_type_name):
        """Get a Face Type instance from its name.

        This method will correct for capitalization as well as the presence of
        spaces and underscores.

        Args:
            face_type_name: A text string for the face type (eg. "Wall").
        """
        if self._type_name_dict is None:
            self._build_type_name_dict()
        try:
            return self._type_name_dict[re.sub(r'[\s_]', '', face_type_name.lower())]
        except KeyError:
            raise ValueError(
                '"{}" is not a valid face type name.\nChoose from the following'
                ': {}'.format(face_type_name, list(self._type_name_dict.keys())))

    def _build_type_name_dict(self):
        """Build a dictionary that can be used to lookup face types by name."""
        attr = [atr for atr in dir(self) if not atr.startswith('_')]
        clean_attr = [re.sub(r'[\s_]', '', atr.lower()) for atr in attr]
        self._type_name_dict = {}
        for atr_name, atr in zip(clean_attr, attr):
            try:
                full_attr = getattr(self, '_' + atr)
                self._type_name_dict[atr_name] = full_attr
            except AttributeError:
                pass  # callable method that has no static default object

    def __contains__(self, value):
        return isinstance(value, _FaceType)

    def __repr__(self):
        attr = [atr for atr in dir(self) if not atr.startswith('_') and atr != 'by_name']
        return 'Face Types:\n{}'.format('\n'.join(attr))


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
