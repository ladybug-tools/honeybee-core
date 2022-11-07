# coding: utf-8
"""Honeybee Door."""
from __future__ import division
import math

from ladybug_geometry.geometry2d.pointvector import Vector2D
from ladybug_geometry.geometry3d.pointvector import Point3D
from ladybug_geometry.geometry3d.face import Face3D
from ladybug.color import Color

from ._basewithshade import _BaseWithShade
from .typing import clean_string
from .properties import DoorProperties
from .boundarycondition import boundary_conditions, Outdoors, Surface
from .shade import Shade
import honeybee.writer.door as writer


class Door(_BaseWithShade):
    """A single planar Door in a Face.

    Args:
        identifier: Text string for a unique Door ID. Must be < 100 characters and
            not contain any spaces or special characters.
        geometry: A ladybug-geometry Face3D.
        boundary_condition: Boundary condition object (Outdoors, Surface, etc.).
            Default: Outdoors.
        is_glass: Boolean to note whether this object is a glass door as opposed
            to an opaque door. Default: False.

    Properties:
        * identifier
        * display_name
        * boundary_condition
        * is_glass
        * indoor_shades
        * outdoor_shades
        * parent
        * top_level_parent
        * has_parent
        * geometry
        * vertices
        * upper_left_vertices
        * triangulated_mesh3d
        * normal
        * center
        * area
        * perimeter
        * min
        * max
        * altitude
        * azimuth
        * type_color
        * bc_color
        * user_data
    """
    __slots__ = ('_geometry', '_parent', '_boundary_condition', '_is_glass')
    TYPE_COLORS = {
        False: Color(160, 150, 100),
        True: Color(128, 204, 255, 100)
    }
    BC_COLORS = {
        'Outdoors': Color(128, 204, 255),
        'Surface': Color(0, 190, 0)
    }

    def __init__(self, identifier, geometry, boundary_condition=None, is_glass=False):
        """A single planar Door in a Face."""
        _BaseWithShade.__init__(self, identifier)  # process the identifier

        # process the geometry
        assert isinstance(geometry, Face3D), \
            'Expected ladybug_geometry Face3D. Got {}'.format(type(geometry))
        self._geometry = geometry
        self._parent = None  # _parent will be set when the Face is added to a Face

        # process the boundary condition and type
        self.boundary_condition = boundary_condition or boundary_conditions.outdoors
        self.is_glass = is_glass

        # initialize properties for extensions
        self._properties = DoorProperties(self)

    @classmethod
    def from_dict(cls, data):
        """Initialize an Door from a dictionary.

        Args:
            data: A dictionary representation of an Door object.
        """
        try:
            # check the type of dictionary
            assert data['type'] == 'Door', 'Expected Door dictionary. ' \
                'Got {}.'.format(data['type'])

            # serialize the door
            is_glass = data['is_glass'] if 'is_glass' in data else False
            if data['boundary_condition']['type'] == 'Outdoors':
                boundary_condition = Outdoors.from_dict(data['boundary_condition'])
            elif data['boundary_condition']['type'] == 'Surface':
                boundary_condition = Surface.from_dict(data['boundary_condition'], True)
            else:
                raise ValueError(
                    'Boundary condition "{}" is not supported for Door.'.format(
                        data['boundary_condition']['type']))
            door = cls(data['identifier'], Face3D.from_dict(data['geometry']),
                       boundary_condition, is_glass)
            if 'display_name' in data and data['display_name'] is not None:
                door.display_name = data['display_name']
            if 'user_data' in data and data['user_data'] is not None:
                door.user_data = data['user_data']
            door._recover_shades_from_dict(data)

            # assign extension properties
            if data['properties']['type'] == 'DoorProperties':
                door.properties._load_extension_attr_from_dict(data['properties'])
            return door
        except Exception as e:
            cls._from_dict_error_message(data, e)

    @classmethod
    def from_vertices(cls, identifier, vertices, boundary_condition=None,
                      is_glass=False):
        """Create a Door from vertices with each vertex as an iterable of 3 floats.

        Args:
            identifier: Text string for a unique Door ID. Must be < 100 characters and
                not contain any spaces or special characters.
            vertices: A flattened list of 3 or more vertices as (x, y, z).
            boundary_condition: Boundary condition object (eg. Outdoors, Surface).
                Default: Outdoors.
            is_glass: Boolean to note whether this object is a glass door as opposed
                to an opaque door. Default: False.
        """
        geometry = Face3D(tuple(Point3D(*v) for v in vertices))
        return cls(identifier, geometry, boundary_condition, is_glass)

    @property
    def boundary_condition(self):
        """Get or set the boundary condition of this door."""
        return self._boundary_condition

    @boundary_condition.setter
    def boundary_condition(self, value):
        if not isinstance(value, Outdoors):
            if isinstance(value, Surface):
                assert len(value.boundary_condition_objects) == 3, 'Surface boundary ' \
                    'condition for Door must have 3 boundary_condition_objects.'
            else:
                raise ValueError('Door only supports Outdoor or Surface boundary '
                                 'condition. Got {}'.format(type(value)))
        self._boundary_condition = value

    @property
    def is_glass(self):
        """Get or set a boolean to note whether this object is a glass door."""
        return self._is_glass

    @is_glass.setter
    def is_glass(self, value):
        try:
            self._is_glass = bool(value)
        except TypeError:
            raise TypeError(
                'Expected boolean for Door.is_glass. Got {}.'.format(value))

    @property
    def parent(self):
        """Get the parent Face if assigned. None if not assigned."""
        return self._parent

    @property
    def top_level_parent(self):
        """Get the top-level parent object if assigned.

        This will be a Room if there is a parent Face that has a parent Room and
        will be a Face if the parent Face is orphaned. Will be None if no parent
        is assigned.
        """
        if self.has_parent:
            if self._parent.has_parent:
                return self._parent._parent
            return self._parent
        return None

    @property
    def has_parent(self):
        """Get a boolean noting whether this Door has a parent Face."""
        return self._parent is not None

    @property
    def geometry(self):
        """Get a ladybug_geometry Face3D object representing the door."""
        return self._geometry

    @property
    def vertices(self):
        """Get a list of vertices for the door (in counter-clockwise order)."""
        return self._geometry.vertices

    @property
    def upper_left_vertices(self):
        """Get a list of vertices starting from the upper-left corner.

        This property should be used when exporting to EnergyPlus / OpenStudio.
        """
        return self._geometry.upper_left_counter_clockwise_vertices

    @property
    def triangulated_mesh3d(self):
        """Get a ladybug_geometry Mesh3D of the door geometry composed of triangles.

        In EnergyPlus / OpenStudio workflows, this property is used to subdivide
        the door when it has more than 4 vertices. This is necessary since
        EnergyPlus cannot accept sub-faces with more than 4 vertices.
        """
        return self._geometry.triangulated_mesh3d

    @property
    def normal(self):
        """Get a ladybug_geometry Vector3D for the direction the door is pointing.
        """
        return self._geometry.normal

    @property
    def center(self):
        """Get a ladybug_geometry Point3D for the center of the door.

        Note that this is the center of the bounding rectangle around this geometry
        and not the area centroid.
        """
        return self._geometry.center

    @property
    def area(self):
        """Get the area of the door."""
        return self._geometry.area

    @property
    def perimeter(self):
        """Get the perimeter of the door."""
        return self._geometry.perimeter

    @property
    def min(self):
        """Get a Point3D for the minimum of the bounding box around the object."""
        return self._min_with_shades(self._geometry)

    @property
    def max(self):
        """Get a Point3D for the maximum of the bounding box around the object."""
        return self._max_with_shades(self._geometry)

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
        return self.TYPE_COLORS[self.is_glass]

    @property
    def bc_color(self):
        """Get a Color to be used in visualizations by boundary condition."""
        return self.BC_COLORS[self.boundary_condition.name]

    def horizontal_orientation(self, north_vector=Vector2D(0, 1)):
        """Get a number between 0 and 360 for the orientation of the door in degrees.

        0 = North, 90 = East, 180 = South, 270 = West

        Args:
            north_vector: A ladybug_geometry Vector2D for the north direction.
                Default is the Y-axis (0, 1).
        """
        return math.degrees(
            north_vector.angle_clockwise(Vector2D(self.normal.x, self.normal.y)))

    def cardinal_direction(self, north_vector=Vector2D(0, 1)):
        """Get text description for the cardinal direction that the door is pointing.

        Will be one of the following: ('North', 'NorthEast', 'East', 'SouthEast',
        'South', 'SouthWest', 'West', 'NorthWest').

        Args:
            north_vector: A ladybug_geometry Vector2D for the north direction.
                Default is the Y-axis (0, 1).
        """
        orient = self.horizontal_orientation(north_vector)
        orient_text = ('North', 'NorthEast', 'East', 'SouthEast', 'South',
                       'SouthWest', 'West', 'NorthWest')
        angles = (22.5, 67.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5)
        for i, ang in enumerate(angles):
            if orient < ang:
                return orient_text[i]
        return orient_text[0]

    def add_prefix(self, prefix):
        """Change the identifier of this object and all child objects by inserting a prefix.

        This is particularly useful in workflows where you duplicate and edit
        a starting object and then want to combine it with the original object
        into one Model (like making a model of repeated rooms) since all objects
        within a Model must have unique identifiers.

        Args:
            prefix: Text that will be inserted at the start of this object's
                (and child objects') identifier and display_name. It is recommended
                that this prefix be short to avoid maxing out the 100 allowable
                characters for honeybee identifiers.
        """
        self._identifier = clean_string('{}_{}'.format(prefix, self.identifier))
        self.display_name = '{}_{}'.format(prefix, self.display_name)
        self.properties.add_prefix(prefix)
        self._add_prefix_shades(prefix)
        if isinstance(self._boundary_condition, Surface):
            new_bc_objs = (clean_string('{}_{}'.format(prefix, adj_name)) for adj_name
                           in self._boundary_condition._boundary_condition_objects)
            self._boundary_condition = Surface(new_bc_objs, True)

    def set_adjacency(self, other_door):
        """Set this door to be adjacent to another (and vice versa).

        Note that this method does not verify whether the other_door geometry is
        co-planar or compatible with this one so it is recommended that a test
        be performed before using this method in order to verify these criteria.
        The Face3D.is_centered_adjacent() or the Face3D.is_geometrically_equivalent()
        methods are both suitable for this purpose.

        Args:
            other_door: Another Door object to be set adjacent to this one.
        """
        assert isinstance(other_door, Door), \
            'Expected Door. Got {}.'.format(type(other_door))
        assert other_door.is_glass is self.is_glass, \
            'Adjacent doors must have matching is_glass properties.'
        self._boundary_condition = boundary_conditions.surface(other_door, True)
        other_door._boundary_condition = boundary_conditions.surface(self, True)

    def overhang(self, depth, angle=0, indoor=False, tolerance=0.01, base_name=None):
        """Add a single overhang for this Door. Can represent entryway awnings.

        Args:
            depth: A number for the overhang depth.
            angle: A number for the for an angle to rotate the overhang in degrees.
                Positive numbers indicate a downward rotation while negative numbers
                indicate an upward rotation. Default is 0 for no rotation.
            indoor: Boolean for whether the overhang should be generated facing the
                opposite direction of the aperture normal (typically meaning
                indoor geometry). Default: False.
            tolerance: An optional value to return None if the overhang has a length less
                than the tolerance. Default: 0.01, suitable for objects in meters.
            base_name: Optional base name for the shade objects. If None, the default
                is InOverhang or OutOverhang depending on whether indoor is True.

        Returns:
            A list of the new Shade objects that have been generated.
        """
        # get a name for the shade
        if base_name is None:
            base_name = 'InOverhang' if indoor else 'OutOverhang'
        shd_name_base = '{}_' + str(base_name) + '{}'

        # create the shade geometry
        angle = math.radians(angle)
        dr_geo = self.geometry if indoor is False else self.geometry.flip()
        shade_faces = dr_geo.contour_fins_by_number(
            1, depth, 0, angle, Vector2D(0, 1), False, tolerance)

        # create the Shade objects
        overhang = []
        for i, shade_geo in enumerate(shade_faces):
            overhang.append(Shade(shd_name_base.format(self.identifier, i), shade_geo))
        if indoor:
            self.add_indoor_shades(overhang)
        else:
            self.add_outdoor_shades(overhang)
        return overhang

    def move(self, moving_vec):
        """Move this Door along a vector.

        Args:
            moving_vec: A ladybug_geometry Vector3D with the direction and distance
                to move the face.
        """
        self._geometry = self.geometry.move(moving_vec)
        self.move_shades(moving_vec)
        self.properties.move(moving_vec)
        self._reset_parent_geometry()

    def rotate(self, axis, angle, origin):
        """Rotate this Door by a certain angle around an axis and origin.

        Args:
            axis: A ladybug_geometry Vector3D axis representing the axis of rotation.
            angle: An angle for rotation in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        self._geometry = self.geometry.rotate(axis, math.radians(angle), origin)
        self.rotate_shades(axis, angle, origin)
        self.properties.rotate(axis, angle, origin)
        self._reset_parent_geometry()

    def rotate_xy(self, angle, origin):
        """Rotate this Door counterclockwise in the world XY plane by a certain angle.

        Args:
            angle: An angle in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        self._geometry = self.geometry.rotate_xy(math.radians(angle), origin)
        self.rotate_xy_shades(angle, origin)
        self.properties.rotate_xy(angle, origin)
        self._reset_parent_geometry()

    def reflect(self, plane):
        """Reflect this Door across a plane.

        Args:
            plane: A ladybug_geometry Plane across which the object will
                be reflected.
        """
        self._geometry = self.geometry.reflect(plane.n, plane.o)
        self.reflect_shades(plane)
        self.properties.reflect(plane)
        self._reset_parent_geometry()

    def scale(self, factor, origin=None):
        """Scale this Door by a factor from an origin point.

        Args:
            factor: A number representing how much the object should be scaled.
            origin: A ladybug_geometry Point3D representing the origin from which
                to scale. If None, it will be scaled from the World origin (0, 0, 0).
        """
        self._geometry = self.geometry.scale(factor, origin)
        self.scale_shades(factor, origin)
        self.properties.scale(factor, origin)
        self._reset_parent_geometry()

    def remove_colinear_vertices(self, tolerance=0.01):
        """Remove all colinear and duplicate vertices from this object's geometry.

        Note that this does not affect any assigned Shades.

        Args:
            tolerance: The minimum distance between a vertex and the boundary segments
                at which point the vertex is considered colinear. Default: 0.01,
                suitable for objects in meters.
        """
        try:
            self._geometry = self.geometry.remove_colinear_vertices(tolerance)
        except AssertionError as e:  # usually a sliver face of some kind
            raise ValueError(
                'Door "{}" is invalid with dimensions less than the '
                'tolerance.\n{}'.format(self.full_id, e))

    def is_geo_equivalent(self, door, tolerance=0.01):
        """Get a boolean for whether this object is geometrically equivalent to another.

        The total number of vertices and the ordering of these vertices can be
        different but the geometries must share the same center point and be
        next to one another to within the tolerance.

        Args:
            door: Another Door for which geometric equivalency will be tested.
            tolerance: The minimum difference between the coordinate values of two
                vertices at which they can be considered geometrically equivalent.

        Returns:
            True if geometrically equivalent. False if not geometrically equivalent.
        """
        if abs(self.area - door.area) > tolerance * self.area:
            return False
        return self.geometry.is_centered_adjacent(door.geometry, tolerance)

    def check_planar(self, tolerance=0.01, raise_exception=True, detailed=False):
        """Check whether all of the Door's vertices lie within the same plane.

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
            msg = 'Door "{}" is not planar.\n{}'.format(self.full_id, e)
            return self._validation_message(
                msg, raise_exception, detailed, '000101',
                error_type='Non-Planar Geometry')
        return [] if detailed else ''

    def check_self_intersecting(self, tolerance=0.01, raise_exception=True,
                                detailed=False):
        """Check whether the edges of the Door intersect one another (like a bowtie).

        Note that objects that have duplicate vertices will not be considered
        self-intersecting and are valid in honeybee.

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
            msg = 'Door "{}" has self-intersecting edges.'.format(self.full_id)
            try:  # see if it is self-intersecting because of a duplicate vertex
                new_geo = self.geometry.remove_colinear_vertices(tolerance)
                if not new_geo.is_self_intersecting:
                    return ''  # removing the duplicate vertex makes it self-intersecting
            except AssertionError:
                pass  # zero area face; treat it as self-intersecting
            return self._validation_message(
                msg, raise_exception, detailed, '000102',
                error_type='Self-Intersecting Geometry')
        return [] if detailed else ''

    def check_non_zero(self, tolerance=0.0001, raise_exception=True, detailed=False):
        """Check whether the area of the Door is above a certain "zero" tolerance.

        Args:
            tolerance: The minimum acceptable area of the object. Default is 0.0001,
                which is equal to 1 cm2 when model units are meters. This is just
                above the smallest size that OpenStudio will accept.
            raise_exception: If True, a ValueError will be raised if the object
                area is below the tolerance. Default: True.
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        if self.area < tolerance:
            msg = 'Door "{}" geometry is too small. Area must be at least {}. ' \
                'Got {}.'.format(self.full_id, tolerance, self.area)
            if raise_exception:
                raise ValueError(msg)
            return self._validation_message(
                msg, raise_exception, detailed, '000103',
                error_type='Zero-Area Geometry')
        return [] if detailed else ''

    def display_dict(self):
        """Get a list of DisplayFace3D dictionaries for visualizing the object."""
        base = [self._display_face(self.geometry, self.type_color)]
        for shd in self.shades:
            base.extend(shd.display_dict())
        return base

    @property
    def to(self):
        """Door writer object.

        Use this method to access Writer class to write the door in different formats.

        Usage:

        .. code-block:: python

            door.to.idf(door) -> idf string.
            door.to.radiance(door) -> Radiance string.
        """
        return writer

    def to_dict(self, abridged=False, included_prop=None, include_plane=True):
        """Return Door as a dictionary.

        Args:
            abridged: Boolean to note whether the extension properties of the
                object (ie. materials, constructions) should be included in detail
                (False) or just referenced by identifier (True). (Default: False).
            included_prop: List of properties to filter keys that must be included in
                output dictionary. For example ['energy'] will include 'energy' key if
                available in properties to_dict. By default all the keys will be
                included. To exclude all the keys from extensions use an empty list.
            include_plane: Boolean to note wether the plane of the Face3D should be
                included in the output. This can preserve the orientation of the
                X/Y axes of the plane but is not required and can be removed to
                keep the dictionary smaller. (Default: True).
        """
        base = {'type': 'Door'}
        base['identifier'] = self.identifier
        base['display_name'] = self.display_name
        base['properties'] = self.properties.to_dict(abridged, included_prop)
        enforce_upper_left = True if 'energy' in base['properties'] else False
        base['geometry'] = self._geometry.to_dict(include_plane, enforce_upper_left)
        base['is_glass'] = self.is_glass
        if isinstance(self.boundary_condition, Outdoors) and \
                'energy' in base['properties']:
            base['boundary_condition'] = self.boundary_condition.to_dict(full=True)
        else:
            base['boundary_condition'] = self.boundary_condition.to_dict()
        self._add_shades_to_dict(base, abridged, included_prop, include_plane)
        if self.user_data is not None:
            base['user_data'] = self.user_data
        return base

    def _reset_parent_geometry(self):
        """Reset parent punched_geometry in the case that the object is transformed."""
        if self.has_parent:
            self._parent._punched_geometry = None

    def __copy__(self):
        new_door = Door(self.identifier, self.geometry, self.boundary_condition,
                        self.is_glass)
        new_door._display_name = self._display_name
        new_door._user_data = None if self.user_data is None else self.user_data.copy()
        self._duplicate_child_shades(new_door)
        new_door._properties._duplicate_extension_attr(self._properties)
        return new_door

    def __repr__(self):
        return 'Door: %s' % self.display_name
