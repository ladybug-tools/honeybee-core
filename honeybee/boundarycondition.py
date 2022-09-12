"""Boundary Condition for Face, Aperture, Door."""
import re

from .typing import float_in_range, tuple_with_length
from .altnumber import autocalculate


class _BoundaryCondition(object):
    """Base boundary condition class."""

    __slots__ = ()

    def __init__(self):
        """Initialize Boundary condition."""


    @property
    def name(self):
        """Get the name of the boundary condition (ie. 'Outdoors', 'Ground')."""
        return self.__class__.__name__

    @property
    def view_factor(self):
        """Get the view factor to the ground."""
        return 'autocalculate'

    @property
    def sun_exposure_idf(self):
        """Get a text string for sun exposure, which is write-able into an IDF."""
        return 'NoSun'

    @property
    def wind_exposure_idf(self):
        """ Get a text string for wind exposure, which is write-able into an IDF."""
        return 'NoWind'

    def to_dict(self):
        """Get the boundary condition as a dictionary."""
        return {'type': self.name}

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        return self.name


class Outdoors(_BoundaryCondition):
    """Outdoor boundary condition.

    Args:
        sun_exposure: A boolean noting whether the boundary is exposed to sun.
            Default: True.
        wind_exposure: A boolean noting whether the boundary is exposed to wind.
            Default: True.
        view_factor: A number between 0 and 1 for the view factor to the ground.
            This input can also be an Autocalculate object to signify that the view
            factor automatically calculated.  Default: autocalculate.
    """

    __slots__ = ('_sun_exposure', '_wind_exposure', '_view_factor')

    def __init__(self, sun_exposure=True, wind_exposure=True,
                 view_factor=autocalculate):
        """Initialize Outdoors boundary condition."""
        assert isinstance(sun_exposure, bool), \
            'Input sun_exposure must be a Boolean. Got {}.'.format(type(sun_exposure))
        self._sun_exposure = sun_exposure
        assert isinstance(wind_exposure, bool), \
            'Input wind_exposure must be a Boolean. Got {}.'.format(type(wind_exposure))
        self._wind_exposure = wind_exposure
        if view_factor == autocalculate:
            self._view_factor = autocalculate
        else:
            self._view_factor = float_in_range(
                view_factor, 0.0, 1.0, 'view factor to ground')

    @classmethod
    def from_dict(cls, data):
        """Initialize Outdoors BoundaryCondition from a dictionary.

        Args:
            data: A dictionary representation of the boundary condition.
        """
        assert data['type'] == 'Outdoors', 'Expected dictionary for Outdoors boundary ' \
            'condition. Got {}.'.format(data['type'])
        sun_exposure = True if 'sun_exposure' not in data else data['sun_exposure']
        wind_exposure = True if 'wind_exposure' not in data else data['wind_exposure']
        view_factor = autocalculate if 'view_factor' not in data or \
            data['view_factor'] == autocalculate.to_dict() else data['view_factor']
        return cls(sun_exposure, wind_exposure, view_factor)

    @property
    def sun_exposure(self):
        """Get a boolean noting whether the boundary is exposed to sun."""
        return self._sun_exposure

    @property
    def wind_exposure(self):
        """Get a boolean noting whether the boundary is exposed to wind."""
        return self._wind_exposure

    @property
    def view_factor(self):
        """Get the view factor to the ground as a number or 'autocalculate'."""
        return self._view_factor

    @property
    def sun_exposure_idf(self):
        """Get a text string for sun exposure, which is write-able into an IDF."""
        return 'NoSun' if not self.sun_exposure else 'SunExposed'

    @property
    def wind_exposure_idf(self):
        """Get a text string for wind exposure, which is write-able into an IDF."""
        return 'NoWind' if not self.wind_exposure else 'WindExposed'

    def to_dict(self, full=False):
        """Get the boundary condition as a dictionary.

        Args:
            full: Set to True to get the full dictionary which includes energy
                simulation specific keys such as sun_exposure, wind_exposure and
                view_factor. (Default: False).
        """
        bc_dict = {'type': self.name}
        if full:
            bc_dict['sun_exposure'] = self.sun_exposure
            bc_dict['wind_exposure'] = self.wind_exposure
            bc_dict['view_factor'] = autocalculate.to_dict() if \
                self.view_factor == autocalculate else self.view_factor
        return bc_dict


class Surface(_BoundaryCondition):
    """Boundary condition when an object is adjacent to another object."""

    __slots__ = ('_boundary_condition_objects',)

    def __init__(self, boundary_condition_objects, sub_face=False):
        """Initialize Surface boundary condition.

        Args:
            boundary_condition_objects: A list of up to 3 object identifiers that are adjacent
                to this one. The first object is always the one that is immediately
                adjacent and is of the same object type (Face, Aperture, Door). When
                this boundary condition is applied to a Face, the second object in the
                tuple will be the parent Room of the adjacent object. When the boundary
                condition is applied to a sub-face (Door or Aperture), the second object
                will be the parent Face of the adjacent sub-face and the third object
                 will be the parent Room of the adjacent sub-face.
            sub_face: Boolean to note whether this boundary condition is applied to a
                sub-face (an Aperture or a Door) instead of a Face. (Default: False).
        """
        if sub_face:
            self._boundary_condition_objects = tuple_with_length(
                boundary_condition_objects, 3, str,
                'boundary_condition_objects for Apertures or Doors')
        else:
            self._boundary_condition_objects = tuple_with_length(
                boundary_condition_objects, 2, str,
                'boundary_condition_objects for Faces')

    @classmethod
    def from_dict(cls, data, sub_face=False):
        """Initialize Surface BoundaryCondition from a dictionary.

        Args:
            data: A dictionary representation of the boundary condition.
            sub_face: Boolean to note whether this boundary condition is applied to a
                sub-face (an Aperture or a Door) instead of a Face. Default: False.
        """
        assert data['type'] == 'Surface', 'Expected dictionary for Surface boundary ' \
            'condition. Got {}.'.format(data['type'])
        return cls(data['boundary_condition_objects'], sub_face)

    @classmethod
    def from_other_object(cls, other_object, sub_face=False):
        """Initialize Surface boundary condition from an adjacent other object.

        Args:
            other_object: Another object (Face, Aperture, Door) of the same type
                that this boundary condition is assigned.  This other_object will be
                set as the adjacent object in this boundary condition.
            sub_face: Boolean to note whether this boundary condition is applied to a
                sub-face (an Aperture or a Door) instead of a Face. Default: False.
        """
        error_msg = 'Surface boundary conditions can only be assigned to objects' \
            ' with parent Rooms.'
        bc_objects = [other_object.identifier]
        if other_object.has_parent:
            bc_objects.append(other_object.parent.identifier)
            if sub_face:
                if other_object.parent.has_parent:
                    bc_objects.append(other_object.parent.parent.identifier)
                else:
                    raise AttributeError(error_msg)
        else:
            raise AttributeError(error_msg)
        return cls(bc_objects, sub_face)

    @property
    def boundary_condition_objects(self):
        """Get a tuple of up to 3 object identifiers that are adjacent to this one.

        The first object is always the one that is immediately adjacent and is of
        the same object type (Face, Aperture, Door).
        When this boundary condition is applied to a Face, the second object in the
        tuple will be the parent Room of the adjacent object.
        When the boundary condition is applied to a sub-face (Door or Aperture),
        the second object will be the parent Face of the sub-face and the third
        object will be the parent Room of the adjacent sub-face.
        """
        return self._boundary_condition_objects

    @property
    def boundary_condition_object(self):
        """Get the identifier of the object adjacent to this one."""
        return self._boundary_condition_objects[0]

    def to_dict(self):
        """Get the boundary condition as a dictionary.

        Args:
            full: Set to True to get the full dictionary which includes energy
                simulation specific keys such as sun_exposure, wind_exposure and
                view_factor. Default: False.
        """
        return {'type': self.name,
                'boundary_condition_objects': self.boundary_condition_objects}


class Ground(_BoundaryCondition):
    """Ground boundary condition.

    Args:
        data: A dictionary representation of the boundary condition.
    """
    __slots__ = ()

    @classmethod
    def from_dict(cls, data):
        """Initialize Ground BoundaryCondition from a dictionary."""
        assert data['type'] == 'Ground', 'Expected dictionary for Ground boundary ' \
            'condition. Got {}.'.format(data['type'])
        return cls()


class _BoundaryConditions(object):
    """Boundary conditions."""

    def __init__(self):
        self._outdoors = Outdoors()
        self._ground = Ground()
        self._bc_name_dict = None

    @property
    def outdoors(self):
        """Default outdoor boundary condition."""
        return self._outdoors

    @property
    def ground(self):
        """Default ground boundary condition."""
        return self._ground

    def surface(self, other_object, sub_face=False):
        """Get a Surface boundary condition.

        Args:
            other_object: The other object that is adjacent to the one that will
                bear this Surface boundary condition.
            sub_face: Boolean to note whether the boundary condition is for a
                sub-face (Aperture or Door) instead of a Face. (Default: False).
        """
        return Surface.from_other_object(other_object, sub_face)

    def by_name(self, bc_name):
        """Get a boundary condition object instance by its name.

        This method will correct for capitalization as well as the presence of
        spaces and underscores. Note that this method only works for boundary
        conditions with all of their inputs defaulted.

        Args:
            bc_name: A boundary condition name.
        """
        if self._bc_name_dict is None:
            self._build_bc_name_dict()
        try:
            return self._bc_name_dict[re.sub(r'[\s_]', '', bc_name.lower())]
        except KeyError:
            raise ValueError(
                '"{}" is not a valid boundary condition name.\nChoose from the '
                'following: {}'.format(bc_name, list(self._bc_name_dict.keys())))

    def _build_bc_name_dict(self):
        """Build a dictionary that can be used to lookup boundary conditions by name."""
        attr = [atr for atr in dir(self) if not atr.startswith('_')]
        clean_attr = [re.sub(r'[\s_]', '', atr.lower()) for atr in attr]
        self._bc_name_dict = {}
        for atr_name, atr in zip(clean_attr, attr):
            try:
                full_attr = getattr(self, '_' + atr)
                self._bc_name_dict[atr_name] = full_attr
            except AttributeError:
                pass  # callable method that has no static default object

    def __contains__(self, value):
        return isinstance(value, _BoundaryCondition)


boundary_conditions = _BoundaryConditions()


def get_bc_from_position(positions, ground_depth=0):
    """Return a boundary condition based on the relationship to a ground plane.

    Positions that are entirely at or below the ground_depth will get a Ground
    boundary condition. If there are any positions above the ground_depth, an
    Outdoors boundary condition will be returned.

    args:
        positions: A list of ladybug_geometry Point3D objects representing the
            vertices of an object.
        ground_depth: The Z value above which positions are considered Outdoors
            instead of Ground.

    Returns:
        Face type instance.
    """
    for position in positions:
        if position.z > ground_depth:
            return boundary_conditions.outdoors
    return boundary_conditions.ground
