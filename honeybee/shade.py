# coding: utf-8
"""Honeybee Shade."""
from __future__ import division
import math

from ladybug_geometry.geometry3d.pointvector import Point3D
from ladybug_geometry.geometry3d.face import Face3D
from ladybug.color import Color

from ._base import _Base
from .typing import clean_string
from .properties import ShadeProperties
import honeybee.writer.shade as writer


class Shade(_Base):
    """A single planar shade.

    Args:
        identifier: Text string for a unique Shade ID. Must be < 100 characters and
            not contain any spaces or special characters.
        geometry: A ladybug-geometry Face3D.
        is_detached: Boolean to note whether this object is detached from other
            geometry. Cases where this should be True include shade representing
            surrounding buildings or context. (Default: False).

    Properties:
        * identifier
        * display_name
        * is_detached
        * parent
        * top_level_parent
        * has_parent
        * is_indoor
        * geometry
        * vertices
        * upper_left_vertices
        * normal
        * center
        * area
        * perimeter
        * min
        * max
        * tilt
        * altitude
        * azimuth
        * type_color
        * bc_color
        * user_data
    """
    __slots__ = ('_geometry', '_parent', '_is_indoor', '_is_detached')
    TYPE_COLORS = {
        (False, False): Color(120, 75, 190),
        (False, True): Color(80, 50, 128),
        (True, False): Color(159, 99, 255),
        (True, True): Color(159, 99, 255)
    }
    BC_COLOR = Color(120, 75, 190)

    def __init__(self, identifier, geometry, is_detached=False):
        """A single planar shade."""
        _Base.__init__(self, identifier)  # process the identifier

        # process the geometry and basic properties
        assert isinstance(geometry, Face3D), \
            'Expected ladybug_geometry Face3D. Got {}'.format(type(geometry))
        self._geometry = geometry
        self._parent = None  # _parent will be set when the Shade is added to an object
        self._is_indoor = False  # this will be set by the _parent
        self.is_detached = is_detached

        # initialize properties for extensions
        self._properties = ShadeProperties(self)

    @classmethod
    def from_dict(cls, data):
        """Initialize an Shade from a dictionary.

        Args:
            data: A dictionary representation of an Shade object.
        """
        try:
            # check the type of dictionary
            assert data['type'] == 'Shade', 'Expected Shade dictionary. ' \
                'Got {}.'.format(data['type'])

            is_detached = data['is_detached'] if 'is_detached' in data else False
            shade = cls(
                data['identifier'], Face3D.from_dict(data['geometry']), is_detached)
            if 'display_name' in data and data['display_name'] is not None:
                shade.display_name = data['display_name']
            if 'user_data' in data and data['user_data'] is not None:
                shade.user_data = data['user_data']

            if data['properties']['type'] == 'ShadeProperties':
                shade.properties._load_extension_attr_from_dict(data['properties'])
            return shade
        except Exception as e:
            cls._from_dict_error_message(data, e)

    @classmethod
    def from_vertices(cls, identifier, vertices, is_detached=False):
        """Create a Shade from vertices with each vertex as an iterable of 3 floats.

        Note that this method is not recommended for a shade with one or more holes
        since the distinction between hole vertices and boundary vertices cannot
        be derived from a single list of vertices.

        Args:
            identifier: Text string for a unique Shade ID. Must be < 100 characters and
                not contain any spaces or special characters.
            vertices: A flattened list of 3 or more vertices as (x, y, z).
            is_detached: Boolean to note whether this object is detached from other
                geometry. Cases where this should be True include shade representing
                surrounding buildings or context. (Default: False).
        """
        geometry = Face3D(tuple(Point3D(*v) for v in vertices))
        return cls(identifier, geometry, is_detached)

    @property
    def is_detached(self):
        """Get or set a boolean for whether this object is detached from other geometry.

        This will automatically be set to False if the shade is assigned to
        parent objects.
        """
        return self._is_detached

    @is_detached.setter
    def is_detached(self, value):
        try:
            self._is_detached = bool(value)
            if self._is_detached:
                assert not self.has_parent, 'Shade cannot be detached when it has ' \
                    'a parent Room, Face, Aperture or Door.'
        except TypeError:
            raise TypeError(
                'Expected boolean for Shade.is_detached. Got {}.'.format(value))

    @property
    def parent(self):
        """Get the parent object if assigned. None if not assigned.

        The parent object can be either a Room, Face, Aperture or Door.
        """
        return self._parent

    @property
    def top_level_parent(self):
        """Get the top-level parent object if assigned.

        This will be the highest-level parent in the hierarchy of the parent-child
        chain. Will be None if no parent is assigned.
        """
        if self.has_parent:
            if self._parent.has_parent:
                if self._parent._parent.has_parent:
                    return self._parent._parent._parent
                return self._parent._parent
            return self._parent
        return None

    @property
    def has_parent(self):
        """Get a boolean noting whether this Shade has a parent object."""
        return self._parent is not None

    @property
    def is_indoor(self):
        """Get a boolean for whether this Shade is on the indoors of its parent object.

        Note that, if there is no parent assigned to this Shade, this property will
        be False.
        """
        return self._is_indoor

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

    @property
    def min(self):
        """Get a Point3D for the minimum of the bounding box around the object."""
        return self._geometry.min

    @property
    def max(self):
        """Get a Point3D for the maximum of the bounding box around the object."""
        return self._geometry.max

    @property
    def tilt(self):
        """Get the tilt of the geometry between 0 (up) and 180 (down)."""
        return math.degrees(self._geometry.tilt)

    @property
    def altitude(self):
        """Get the altitude of the geometry between +90 (up) and -90 (down)."""
        return math.degrees(self._geometry.altitude)

    @property
    def azimuth(self):
        """Get the azimuth of the geometry, between 0 and 360.

        Given Y-axis as North, 0 = North, 90 = East, 180 = South, 270 = West
        This will be zero if the Face3D is perfectly horizontal.
        """
        return math.degrees(self._geometry.azimuth)

    @property
    def type_color(self):
        """Get a Color to be used in visualizations by type."""
        return self.TYPE_COLORS[(self.is_indoor, self.is_detached)]

    @property
    def bc_color(self):
        """Get a Color to be used in visualizations by boundary condition."""
        return self.BC_COLOR

    def add_prefix(self, prefix):
        """Change the identifier of this object by inserting a prefix.

        This is particularly useful in workflows where you duplicate and edit
        a starting object and then want to combine it with the original object
        into one Model (like making a model of repeated rooms) since all objects
        within a Model must have unique identifiers.

        Args:
            prefix: Text that will be inserted at the start of this object's identifier
                and display_name. It is recommended that this prefix be short to
                avoid maxing out the 100 allowable characters for honeybee identifiers.
        """
        self._identifier = clean_string('{}_{}'.format(prefix, self.identifier))
        self.display_name = '{}_{}'.format(prefix, self.display_name)
        self.properties.add_prefix(prefix)

    def move(self, moving_vec):
        """Move this Shade along a vector.

        Args:
            moving_vec: A ladybug_geometry Vector3D with the direction and distance
                to move the face.
        """
        self._geometry = self.geometry.move(moving_vec)
        self.properties.move(moving_vec)

    def rotate(self, axis, angle, origin):
        """Rotate this Shade by a certain angle around an axis and origin.

        Args:
            axis: A ladybug_geometry Vector3D axis representing the axis of rotation.
            angle: An angle for rotation in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        self._geometry = self.geometry.rotate(axis, math.radians(angle), origin)
        self.properties.rotate(axis, angle, origin)

    def rotate_xy(self, angle, origin):
        """Rotate this Shade counterclockwise in the world XY plane by a certain angle.

        Args:
            angle: An angle in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        self._geometry = self.geometry.rotate_xy(math.radians(angle), origin)
        self.properties.rotate_xy(angle, origin)

    def reflect(self, plane):
        """Reflect this Shade across a plane.

        Args:
            plane: A ladybug_geometry Plane across which the object will
                be reflected.
        """
        self._geometry = self.geometry.reflect(plane.n, plane.o)
        self.properties.reflect(plane)

    def scale(self, factor, origin=None):
        """Scale this Shade by a factor from an origin point.

        Args:
            factor: A number representing how much the object should be scaled.
            origin: A ladybug_geometry Point3D representing the origin from which
                to scale. If None, it will be scaled from the World origin (0, 0, 0).
        """
        self._geometry = self.geometry.scale(factor, origin)
        self.properties.scale(factor, origin)

    def remove_colinear_vertices(self, tolerance=0.01):
        """Remove all colinear and duplicate vertices from this object's geometry.

        Args:
            tolerance: The minimum distance between a vertex and the boundary segments
                at which point the vertex is considered colinear. Default: 0.01,
                suitable for objects in meters.
        """
        try:
            self._geometry = self.geometry.remove_colinear_vertices(tolerance)
        except AssertionError as e:  # usually a sliver face of some kind
            raise ValueError(
                'Shade "{}" is invalid with dimensions less than the '
                'tolerance.\n{}'.format(self.full_id, e))

    def is_geo_equivalent(self, shade, tolerance=0.01):
        """Get a boolean for whether this object is geometrically equivalent to another.

        The total number of vertices and the ordering of these vertices can be
        different but the geometries must share the same center point and be
        next to one another to within the tolerance.

        Args:
            shade: Another Shade for which geometric equivalency will be tested.
            tolerance: The minimum difference between the coordinate values of two
                vertices at which they can be considered geometrically equivalent.

        Returns:
            True if geometrically equivalent. False if not geometrically equivalent.
        """
        meta_1 = (self.display_name, self.is_detached)
        meta_2 = (shade.display_name, shade.is_detached)
        if meta_1 != meta_2:
            return False
        if abs(self.area - shade.area) > tolerance * self.area:
            return False
        return self.geometry.is_centered_adjacent(shade.geometry, tolerance)

    def check_planar(self, tolerance=0.01, raise_exception=True, detailed=False):
        """Check whether all of the Shade's vertices lie within the same plane.

        Args:
            tolerance: The minimum distance between a given vertex and a the
                object's plane at which the vertex is said to lie in the plane.
                Default: 0.01, suitable for objects in meters.
            raise_exception: Boolean to note whether an ValueError should be
                raised if a vertex does not lie within the object's plane.
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        try:
            self.geometry.check_planar(tolerance, raise_exception=True)
        except ValueError as e:
            msg = 'Shade "{}" is not planar.\n{}'.format(self.full_id, e)
            full_msg = self._validation_message(
                msg, raise_exception, detailed, '000101',
                error_type='Non-Planar Geometry')
            if detailed:  # add the out-of-plane points to helper_geometry
                help_pts = [
                    p.to_dict() for p in self.geometry.non_planar_vertices(tolerance)
                ]
                full_msg[0]['helper_geometry'] = help_pts
            return full_msg
        return [] if detailed else ''

    def check_self_intersecting(self, tolerance=0.01, raise_exception=True,
                                detailed=False):
        """Check whether the edges of the Shade intersect one another (like a bowtie).

        Args:
            tolerance: The minimum difference between the coordinate values of two
                vertices at which they can be considered equivalent. Default: 0.01,
                suitable for objects in meters.
            raise_exception: If True, a ValueError will be raised if the object
                intersects with itself. Default: True.
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        if self.geometry.is_self_intersecting:
            msg = 'Shade "{}" has self-intersecting edges.'.format(self.full_id)
            try:  # see if it is self-intersecting because of a duplicate vertex
                new_geo = self.geometry.remove_duplicate_vertices(tolerance)
                if not new_geo.is_self_intersecting:
                    return [] if detailed else ''  # valid with removed dup vertex
            except AssertionError:
                return [] if detailed else ''  # degenerate geometry
            full_msg = self._validation_message(
                msg, raise_exception, detailed, '000102',
                error_type='Self-Intersecting Geometry')
            if detailed:  # add the self-intersection points to helper_geometry
                help_pts = [p.to_dict() for p in self.geometry.self_intersection_points]
                full_msg[0]['helper_geometry'] = help_pts
            return full_msg
        return [] if detailed else ''

    def display_dict(self):
        """Get a list of DisplayFace3D dictionaries for visualizing the object."""
        return [self._display_face(self.geometry, self.type_color)]

    @property
    def to(self):
        """Shade writer object.

        Use this method to access Writer class to write the shade in different formats.

        Usage:

        .. code-block:: python

            shade.to.idf(shade) -> idf string.
            shade.to.radiance(shade) -> Radiance string.
        """
        return writer

    def to_dict(self, abridged=False, included_prop=None, include_plane=True):
        """Return Shade as a dictionary.

        Args:
            abridged: Boolean to note whether the extension properties of the
                object (ie. modifiers, transmittance schedule) should be included in
                detail (False) or just referenced by identifier (True). Default: False.
            included_prop: List of properties to filter keys that must be included in
                output dictionary. For example ['energy'] will include 'energy' key if
                available in properties to_dict. By default all the keys will be
                included. To exclude all the keys from extensions use an empty list.
            include_plane: Boolean to note wether the plane of the Face3D should be
                included in the output. This can preserve the orientation of the
                X/Y axes of the plane but is not required and can be removed to
                keep the dictionary smaller. (Default: True).
        """
        base = {'type': 'Shade'}
        base['identifier'] = self.identifier
        base['display_name'] = self.display_name
        base['properties'] = self.properties.to_dict(abridged, included_prop)
        enforce_upper_left = True if 'energy' in base['properties'] else False
        base['geometry'] = self._geometry.to_dict(include_plane, enforce_upper_left)
        if self.is_detached:
            base['is_detached'] = self.is_detached
        if self.user_data is not None:
            base['user_data'] = self.user_data
        return base

    def __copy__(self):
        new_shade = Shade(self.identifier, self.geometry, self.is_detached)
        new_shade._display_name = self._display_name
        new_shade._user_data = None if self.user_data is None else self.user_data.copy()
        new_shade._properties._duplicate_extension_attr(self._properties)
        return new_shade

    def __repr__(self):
        return 'Shade: %s' % self.display_name
