"""Face Properties."""
from .facetype import face_types


class Properties(object):
    """Geometry Properties.

    Base class for geometry properties. This class will be extended by plugins.

    prop = Properties(srf_type)
    prop.radiance -> RadianceProperties
    prop.energy -> EnergyProperties
    """
    TYPES = face_types

    # TODO(): face_type should be required. I will update this after Face class is
    # updated to support type based on normal direction.
    def __init__(self, face_type=None):
        self.face_type = face_type or self.TYPES.wall

    @property
    def face_type(self):
        """Get and set Surface Type."""
        return self._face_type

    @face_type.setter
    def face_type(self, value):
        assert value in self.TYPES, '{} is not a valid type.'.format(value)
        self._face_type = value

    @property
    def to_dict(self):
        exclude = ['to_dict']
        base = {
            'type': 'FaceProperties',
            'face_type': self.face_type.name
        }
        attr = [
            atr for atr in dir(self) if not atr.startswith('_') and atr not in exclude
        ]
        for atr in attr:
            var = getattr(self, atr)
            if not hasattr(var, 'to_dict'):
                continue
            base.update(var.to_dict)
        return base

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Properties representation."""
        return 'FaceProperties:%s' % str(self.face_type.name)
