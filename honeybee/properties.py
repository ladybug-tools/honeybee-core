"""Face Properties."""
from .facetype import face_types
from .boundarycondition import _BoundaryCondition, boundary_conditions


class Properties(object):
    """Geometry Properties.

    Base class for geometry properties. This class will be extended by plugins.

    prop = Properties(srf_type, boundary_condition)
    prop.radiance -> RadianceProperties
    prop.energy -> EnergyProperties
    """
    TYPES = face_types

    def __init__(self, face_type, boundary_condition=None):
        self.face_type = face_type
        self.boundary_condition = boundary_condition or boundary_conditions.outdoors

    @property
    def face_type(self):
        """Get and set Surface Type."""
        return self._face_type

    @face_type.setter
    def face_type(self, value):
        assert value in self.TYPES, '{} is not a valid type.'.format(value)
        self._face_type = value

    @property
    def boundary_condition(self):
        """Get and set boundary condition."""
        return self._boundary_condition

    @boundary_condition.setter
    def boundary_condition(self, bc):
        assert isinstance(bc, _BoundaryCondition), \
            'Expected BoundaryCondition not {}'.format(type(bc))
        self._boundary_condition = bc

    def to_dict(self, include=None):
        """convert properties to dictionary.

        args:
            include: A list of keys to be included in dictionary besides face_type
                and boundary condition. If None all the available keys will be included.
        """
        base = {
            'type': 'FaceProperties',
            'face_type': self.face_type.name
        }

        if include is not None:
            attr = include
        else:
            attr = [atr for atr in dir(self) if not atr.startswith('_')]

        for atr in attr:
            var = getattr(self, atr)
            if not hasattr(var, 'to_dict'):
                continue
            try:
                base.update(var.to_dict())
            except Exception as e:
                raise Exception(
                    'Failed to convert {} to a dict: {}'.format(var, e)
                )

        if 'energy' in base:
            base['boundary_condition'] = self.boundary_condition.to_dict(full=True)
        else:
            base['boundary_condition'] = self.boundary_condition.to_dict(full=False)
        return base

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Properties representation."""
        return 'FaceProperties:%s' % str(self.face_type.name)
