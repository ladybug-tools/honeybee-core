# coding: utf-8
"""Honeybee Shade."""
from ._base import _Base
from .properties import ShadeProperties
import honeybee.writer as writer

from ladybug_geometry.geometry3d.pointvector import Point3D
from ladybug_geometry.geometry3d.face import Face3D

import math


class Shade(_Base):
    """A single planar shade.

    Properties:
        * name
        * display_name
        * parent
        * has_parent
        * geometry
        * vertices
        * upper_left_vertices
        * normal
        * center
        * area
        * perimeter
    """
    __slots__ = ('_geometry', '_parent')

    def __init__(self, name, geometry):
        """A single planar shade.

        Args:
            name: Shade name. Must be < 100 characters.
            geometry: A ladybug-geometry Face3D.
        """
        _Base.__init__(self, name)  # process the name

        # process the geometry
        assert isinstance(geometry, Face3D), \
            'Expected ladybug_geometry Face3D. Got {}'.format(type(geometry))
        self._geometry = geometry
        self._parent = None  # _parent will be set when the Shade is added to a Room

        # initialize properties for extensions
        self._properties = ShadeProperties(self)

    @classmethod
    def from_dict(cls, data):
        """Initialize an Shade from a dictionary.

        Args:
            data: A dictionary representation of an Shade object.
        """
        # check the type of dictionary
        assert data['type'] == 'Shade', 'Expected Shade dictionary. ' \
            'Got {}.'.format(data['type'])

        shade = cls(data['name'], Face3D.from_dict(data['geometry']))
        if 'display_name' in data and data['display_name'] is not None:
            shade._display_name = data['display_name']

        if data['properties']['type'] == 'ShadeProperties':
            shade.properties._load_extension_attr_from_dict(data['properties'])
        return shade

    @classmethod
    def from_vertices(cls, name, vertices):
        """Create a Shade from vertices with each vertex as an iterable of 3 floats.

        Note that this method is not recommended for a shade with one or more holes
        since the distinction between hole vertices and boundary vertices cannot
        be derived from a single list of vertices.

        Args:
            name: Shade name.
            vertices: A flattened list of 3 or more vertices as (x, y, z).
        """
        geometry = Face3D(tuple(Point3D(*v) for v in vertices))
        return cls(name, geometry)

    @property
    def parent(self):
        """Get the parent Room if assigned. None if not assigned."""
        return self._parent

    @property
    def has_parent(self):
        """Get a boolean noting whether this Shade has a parent Room."""
        return self._parent is not None

    @property
    def geometry(self):
        """Get a ladybug_geometry Face3D object representing the Shade."""
        return self._geometry

    @property
    def vertices(self):
        """Get a list of vertices for the shade (in counter-clockwise order)."""
        return self._geometry.vertices

    @property
    def upper_left_vertices(self):
        """Get a list of vertices starting from the upper-left corner.

        This property should be used when exporting to EnergyPlus / OpenStudio.
        """
        return self._geometry.upper_left_counter_clockwise_vertices

    @property
    def normal(self):
        """Get a ladybug_geometry Vector3D for the direction the shade is pointing.
        """
        return self._geometry.normal

    @property
    def center(self):
        """Get a ladybug_geometry Point3D for the center of the shade.

        Note that this is the center of the bounding rectangle around this geometry
        and not the area centroid.
        """
        return self._geometry.center

    @property
    def area(self):
        """Get the area of the shade."""
        return self._geometry.area

    @property
    def perimeter(self):
        """Get the perimeter of the shade."""
        return self._geometry.perimeter

    def move(self, moving_vec):
        """Move this Shade along a vector.

        Args:
            moving_vec: A ladybug_geometry Vector3D with the direction and distance
                to move the face.
        """
        self._geometry = self.geometry.move(moving_vec)

    def rotate(self, axis, angle, origin):
        """Rotate this Shade by a certain angle around an axis and origin.

        Args:
            axis: A ladybug_geometry Vector3D axis representing the axis of rotation.
            angle: An angle for rotation in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        self._geometry = self.geometry.rotate(axis, math.radians(angle), origin)

    def rotate_xy(self, angle, origin):
        """Rotate this Shade counterclockwise in the world XY plane by a certain angle.

        Args:
            angle: An angle in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        self._geometry = self.geometry.rotate_xy(math.radians(angle), origin)

    def reflect(self, plane):
        """Reflect this Shade across a plane.

        Args:
            plane: A ladybug_geometry Plane across which the object will
                be reflected.
        """
        self._geometry = self.geometry.reflect(plane.n, plane.o)

    def scale(self, factor, origin=None):
        """Scale this Shade by a factor from an origin point.

        Args:
            factor: A number representing how much the object should be scaled.
            origin: A ladybug_geometry Point3D representing the origin from which
                to scale. If None, it will be scaled from the World origin (0, 0, 0).
        """
        self._geometry = self.geometry.scale(factor, origin)

    def check_planar(self, tolerance, raise_exception=True):
        """Check whether all of the Shade's vertices lie within the same plane.

        Args:
            tolerance: The minimum distance between a given vertex and a the
                object's's plane at which the vertex is said to lie in the plane.
            raise_exception: Boolean to note whether an ValueError should be
                raised if a vertex does not lie within the object's plane.
        """
        try:
            return self.geometry.check_planar(tolerance, raise_exception)
        except ValueError as e:
            raise ValueError('Shade "{}" is not planar.\n{}'.format(
                self.display_name, e))

    def check_self_intersecting(self, raise_exception=True):
        """Check whether the edges of the Shade intersect one another (like a bowtwie).

        Args:
            raise_exception: If True, a ValueError will be raised if the object
                intersects with itself. Default: True.
        """
        if self.geometry.is_self_intersecting:
            if raise_exception:
                raise ValueError('Shade "{}" has self-intersecting edges.'.format(
                    self.display_name))
            return False
        return True

    def check_non_zero(self, tolerance=0.0001, raise_exception=True):
        """Check whether the area of the Shade is above a certain "zero" tolerance.

        Args:
            tolerance: The minimum acceptable area of the object. Default is 0.0001,
                which is equal to 1 cm2 when model units are meters. This is just
                above the smalest size that OpenStudio will accept.
            raise_exception: If True, a ValueError will be raised if the object
                area is below the tolerance. Default: True.
        """
        if self.area < tolerance:
            if raise_exception:
                raise ValueError(
                    'Shade "{}" geometry is too small. Area must be at least {}. '
                    'Got {}.'.format(self.display_name, tolerance, self.area))
            return False
        return True

    @property
    def to(self):
        """Shade writer object.

        Use this method to access Writer class to write the shade in different formats.

        Usage:
            shade.to.idf(shade) -> idf string.
            shade.to.radiance(shade) -> Radiance string.
        """
        return writer

    def to_dict(self, abridged=False, included_prop=None):
        """Return Shade as a dictionary.

        Args:
            abridged: Boolean to note whether the extension properties of the
                object (ie. materials, transmittance schedule) should be included in
                detail (False) or just referenced by name (True). Default: False.
            included_prop: List of properties to filter keys that must be included in
                output dictionary. For example ['energy'] will include 'energy' key if
                available in properties to_dict. By default all the keys will be
                included. To exclude all the keys from extensions use an empty list.
        """
        base = {'type': 'Shade'}
        base['name'] = self.name
        base['display_name'] = self.display_name
        base['properties'] = self.properties.to_dict(abridged, included_prop)
        if 'energy' in base['properties']:
            base['geometry'] = self._geometry.to_dict(False, True)  # enforce upper-left
        else:
            base['geometry'] = self._geometry.to_dict(False)
        return base

    def __copy__(self):
        new_shade = Shade(self.name, self.geometry)
        new_shade._display_name = self.display_name
        new_shade._properties._duplicate_extension_attr(self._properties)
        return new_shade

    def __repr__(self):
        return 'Shade: %s' % self.display_name
