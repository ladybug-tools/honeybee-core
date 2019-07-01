"""Boundary Condition for Face, Aperture, Door."""
from .typing import float_in_range


class _BoundaryCondition(object):
    """Base boundary condition class."""

    __slots__ = (
        '_sun_exposure', '_wind_exposure', '_view_factor')

    def __init__(self, sun_exposure=False, wind_exposure=False,
                 view_factor='autocalculate'):
        """Initialize Boundary condition.

        Args:
            sun_exposure: A boolean noting whether the boundary is exposed to sun.
                Default: False.
            wind_exposure: A boolean noting whether the boundary is exposed to wind.
                Default: False.
            view_factor: A number between 0 and 1 for the view factor to the ground.
                This input can also be the word 'autocalculate' to have the view
                factor automatically calculated.  Default: 'autocalculate'.
        """
        assert isinstance(sun_exposure, bool), \
            'Input sun_exposure must be a Boolean. Got {}.'.format(type(sun_exposure))
        self._sun_exposure = sun_exposure
        assert isinstance(wind_exposure, bool), \
            'Input wind_exposure must be a Boolean. Got {}.'.format(type(wind_exposure))
        self._wind_exposure = wind_exposure
        if view_factor == 'autocalculate':
            self._view_factor = view_factor
        else:
            self._view_factor = float_in_range(
                view_factor, 0.0, 1.0, 'view factor to ground')

    @property
    def name(self):
        """Name of the boundary condition (ie. 'Outdoors', 'Ground')."""
        return self.__class__.__name__

    @property
    def sun_exposure(self):
        """A boolean noting whether the boundary is exposed to sun."""
        return self._sun_exposure

    @property
    def wind_exposure(self):
        """A boolean noting whether the boundary is exposed to wind."""
        return self._wind_exposure

    @property
    def view_factor(self):
        """The view factor to the ground as a number or 'autocalculate'."""
        return self._view_factor

    @property
    def sun_exposure_idf(self):
        """Text string for sun exposure, which is write-able into an IDF."""
        return 'NoSun' if not self.wind_exposure else 'SunExposed'

    @property
    def wind_exposure_idf(self):
        """Text string for wind exposure, which is write-able into an IDF."""
        return 'NoWind' if not self.wind_exposure else 'WindExposed'

    def to_dict(self, full=False):
        """Boundary condition as a dictionary.

        Args:
            full: Set to True to get the full dictionary which includes energy
                simulation specific keys such as sun_exposure, wind_exposure and
                view_factor. Default: False.
        """
        if full:
            bc_dict = {
                'type': self.name,
                'sun_exposure': self.sun_exposure_idf,
                'wind_exposure': self.wind_exposure_idf,
                'view_factor': self.view_factor
            }
        else:
            bc_dict = {
                'type': self.name,
            }
        if hasattr(self, 'boundary_condition_object'):  # Surface boundary condition
            bc_dict['bc_object'] = self.boundary_condition_object
        return bc_dict

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return self.name


class Surface(_BoundaryCondition):
    """Bondary condition when an object is adjacent to another object."""

    __slots__ = ('_boundary_condition_objects',)

    def __init__(self, other_object):
        """Initialize Surface boundary condition.

        Args:
            other_object: Another object (Face, Aperture, Door) of the same type
                that this boundary condition is assigned.  This other_object will be
                set as the adjacent object in this boundary condition.
        """
        _BoundaryCondition.__init__(self)
        self._boundary_condition_objects = []
        if other_object is not None:
            self._boundary_condition_objects.append(other_object.name)
            if other_object.has_parent:
                self._boundary_condition_objects.append(other_object.parent.name)
                if other_object.parent.has_parent:
                    self._boundary_condition_objects.append(
                        other_object.parent.parent.name)

    @property
    def boundary_condition_objects(self):
        """A tuple of up to 3 object names that are adjacent to this one.

        The first object is always the one that is immediately adjacet and is of
        the same object type (Face, Aperture, Door).
        When this boundary condition is applied to a Face, the second object in the
        tuple will be the parent Room of the adjacent object.
        When the boundary condition is allplied to a sub-face (Door or Aperture),
        the second object will be the parent Face of the sub-face and the third
        object will be the parent Room of the adjacent sub-face.
        """
        return tuple(self._boundary_condition_objects)

    @property
    def boundary_condition_object(self):
        """The name of the object adjacent to this one."""
        return self._boundary_condition_objects[0]


class Outdoors(_BoundaryCondition):
    """Outdoor boundary condition."""
    __slots__ = ()

    def __init__(self, sun_exposure=True, wind_exposure=True,
                 view_factor='autocalculate'):
        """Initialize Outdoors boundary condition.

        Args:
            sun_exposure: A boolean noting whether the boundary is exposed to sun.
                Default: True.
            wind_exposure: A boolean noting whether the boundary is exposed to wind.
                Default: True.
            view_factor: A number between 0 and 1 for the view factor to the ground.
                This input can also be the word 'autocalculate' to have the view
                factor automatically calculated.  Default: 'autocalculate'.
        """
        _BoundaryCondition.__init__(self, sun_exposure, wind_exposure, view_factor)


class Ground(_BoundaryCondition):
    """Ground boundary condition."""
    __slots__ = ()
    pass


class _BoundaryConditions(object):
    """Boundary conditions."""

    def __init__(self):
        self._outdoors = Outdoors()
        self._ground = Ground()

    @property
    def outdoors(self):
        return self._outdoors

    @property
    def ground(self):
        return self._ground

    def surface(self, other_object):
        return Surface(other_object)

    def __contains__(self, value):
        return isinstance(value, _BoundaryCondition)


boundary_conditions = _BoundaryConditions()


def get_bc_from_position(positions, ground_depth=0):
    """Return a boundary condition based on the relationship to a gound plane.

    Positions that are entirely at or below the ground_depth will get a Ground
    boundary condition. If there are any positions above the ground_depth, an
    Outdoors boundary condition will be returned.

    args:
        positions: A list of ladybug_geometry Point3D objects represeting the
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
