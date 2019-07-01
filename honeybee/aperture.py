# coding: utf-8
"""Honeybee Aperture."""
from .properties import ApertureProperties
from .aperturetype import aperture_types
from .boundarycondition import boundary_conditions, Outdoors, Surface
from .shade import Shade
from .typing import valid_string
import honeybee.writer as writer

from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.plane import Plane
from ladybug_geometry.geometry3d.face import Face3D

import math


class Aperture(object):
    """A single planar aperture face.

    Properties:
        name
        name_original
        geometry
        vertices
        upper_left_vertices
        triangulated_mesh3d
        normal
        center
        area
        perimeter
        type
        boundary_condition
        parent
        has_parent
    """
    TYPES = aperture_types
    __slots__ = ('_name', '_name_original', '_geometry', '_parent',
                 '_type', '_boundary_condition', '_properties')

    def __init__(self, name, geometry, type=None, boundary_condition=None):
        """A single planar aperture in a face.

        Args:
            name: Aperture name. Must be < 100 characters.
            geometry: A ladybug-geometry Face3D.
            type: Aperture type. Default: Window
            boundary_condition: Boundary condition object (Outdoors, Surface).
                Default: Outdoors.
        """
        # process the name
        self._name = valid_string(name, 'honeybee aperture name')
        self._name_original = name

        # process the geometry
        assert isinstance(geometry, Face3D), \
            'Expected ladybug_geometry Face3D. Got {}'.format(type(geometry))
        self._geometry = geometry
        self._parent = None  # _parent will be set when the Aperture is added to a Face

        # process the type and boundary condition
        self.type = type or aperture_types.window
        self.boundary_condition = boundary_condition or boundary_conditions.outdoors

        # initialize properties for extensions
        self._properties = ApertureProperties(self)

    @classmethod
    def from_vertices(cls, name, vertices, type=None, boundary_condition=None):
        """Create an Aperture from vertices with each vertex as an iterable of 3 floats.

        Args:
            name: Aperture name. Must be < 100 characters.
            vertices: A flattened list of 3 or more vertices as (x, y, z).
            type: Aperture type. Default: Window
            boundary_condition: Boundary condition object (eg. Outdoors, Surface).
                Default: Outdoors.
        """
        geometry = Face3D(tuple(Point3D(*v) for v in vertices))
        return cls(name, geometry, type, boundary_condition)

    @property
    def name(self):
        """The aperture name (including only legal characters)."""
        return self._name

    @property
    def name_original(self):
        """Original input name by user.

        If there are no illegal characters in name then name and name_original will
        be the same. Legal characters are ., A-Z, a-z, 0-9, _ and -.
        Invalid characters are automatically removed from the original name for
        compatability with simulation engines.
        """
        return self._name_original

    @property
    def geometry(self):
        """A ladybug_geometry Face3D object representing the aperture."""
        return self._geometry

    @property
    def vertices(self):
        """List of vertices for the aperture (in counter-clockwise order)."""
        return self._geometry.vertices

    @property
    def upper_left_vertices(self):
        """List of vertices starting from the upper-left corner.

        This property should be used when exporting to EnergyPlus / OpenStudio.
        """
        return self._geometry.upper_left_counter_clockwise_vertices

    @property
    def triangulated_mesh3d(self):
        """A ladybug_geometry Mesh3D of the aperture geometry composed of triangles.

        In EnergyPlus / OpenStudio workflows, this property is used to subdivide
        the aperture when it has more than 4 vertices. This is necessary since
        EnergyPlus cannot accept sub-faces with more than 4 vertices.
        """
        return self._geometry.triangulated_mesh3d

    @property
    def normal(self):
        """A ladybug_geometry Vector3D for the direction the aperture is pointing.
        """
        return self._geometry.normal

    @property
    def center(self):
        """A ladybug_geometry Point3D for the center of the aperture.

        Note that this is the center of the bounding rectangle around this geometry
        and not the area centroid.
        """
        return self._geometry.center

    @property
    def area(self):
        """The area of the aperture."""
        return self._geometry.area

    @property
    def perimeter(self):
        """The perimeter of the aperture."""
        return self._geometry.perimeter

    @property
    def type(self):
        """Object for Type of Aperture (ie. Window)."""
        return self._type

    @type.setter
    def type(self, value):
        assert value in self.TYPES, '{} is not a valid face type.'.format(value)
        self._type = value

    @property
    def boundary_condition(self):
        """Boundary condition of this aperture."""
        return self._boundary_condition

    @boundary_condition.setter
    def boundary_condition(self, value):
        assert isinstance(value, (Outdoors, Surface)), \
            'Aperture only supports Outdoor or Surface boundary condition. ' \
            'Got {}'.format(type(value))
        self._boundary_condition = value

    @property
    def parent(self):
        """Parent Face if assigned. None if not assigned."""
        return self._parent

    @property
    def has_parent(self):
        """Boolean noting whether this Aperture has a parent Face."""
        return self._parent is not None

    def set_adjacency(self, other_aperture):
        """Set this aperture to be adjacent to another.

        Note that this method does not verify whether the other_aperture geometry is
        co-planar or compatible with this one so it is recommended that a test
        be performed before using this method in order to verify these criteria.
        The Face3D.is_centered_adjacent() or the Face3D.is_geometrically_equivalent()
        methods are both suitable for this purpose.

        Args:
            other_aperture: Another Aperture object to be set adjacent to this one.
        """
        assert isinstance(other_aperture, Aperture), \
            'Expected Aperture. Got {}.'.format(type(other_aperture))
        self.boundary_condition = Surface(other_aperture)
        other_aperture.boundary_condition = Surface(self)

    def overhang(self, depth, angle=0, indoor=False, tolerance=0):
        """Get a single overhang for this Aperture.

        Args:
            depth: A number for the overhang depth.
            angle: A number for the for an angle to rotate the overhang in degrees.
                Default is 0 for no rotation.
            indoor: Boolean for whether the overhang should be generated facing the
                opposite direction of the aperture normal (typically meaning
                indoor geometry). Default: False.
            tolerance: An optional value to return None if the overhang has a length less
                than the tolerance. Default is 0, which will always yeild an overhang.

        Returns:
            overhang: A Shade object for the Aperture overhang. You may want to run
                the check_non_zero() method on the resulting Shade to verify
                the geometry is subtantial when the Aperture does not have a flat top.
        """
        overhang = self.louvers_by_number(
            1, depth, angle=angle, indoor=indoor, tolerance=tolerance)
        return overhang[0] if len(overhang) != 0 else None

    def right_fin(self, depth, angle=0, indoor=False, tolerance=0):
        """Get a single vertical fin on the right side of this Aperture.

        Args:
            depth: A number for the fin depth.
            angle: A number for the for an angle to rotate the fin in degrees.
                Default is 0 for no rotation.
            indoor: Boolean for whether the fin should be generated facing the
                opposite direction of the aperture normal (typically meaning
                indoor geometry). Default: False.
            tolerance: An optional value to return None if the fin has a length less
                than the tolerance. Default is 0, which will always yeild a fin.

        Returns:
            fin: A Shade object for the Aperture fin. You may want to run
                the check_non_zero() method on the resulting Shade to verify
                the geometry is subtantial when the Aperture does not have a
                flat right side.
        """
        fin = self.louvers_by_number(
            1, depth, angle=angle, contour_vector=Vector3D(1, 0, 0),
            indoor=indoor, tolerance=tolerance)
        return fin[0] if len(fin) != 0 else None

    def left_fin(self, depth, angle=0, indoor=False, tolerance=0):
        """Get a single vertical fin on the left side of this Aperture.

        Args:
            depth: A number for the fin depth.
            angle: A number for the for an angle to rotate the fin in degrees.
                Default is 0 for no rotation.
            indoor: Boolean for whether the fin should be generated facing the
                opposite direction of the aperture normal (typically meaning
                indoor geometry). Default: False.
            tolerance: An optional value to return None if the fin has a length less
                than the tolerance. Default is 0, which will always yeild a fin.

        Returns:
            fin: A Shade object for the Aperture fin. You may want to run
                the check_non_zero() method on the resulting Shade to verify
                the geometry is subtantial when the Aperture does not have a
                flat right side.
        """
        fin = self.louvers_by_number(
            1, depth, angle=angle, contour_vector=Vector3D(1, 0, 0),
            flip_start_side=True, indoor=indoor, tolerance=tolerance)
        return fin[0] if len(fin) != 0 else None

    def extruded_border(self, depth, indoor=False):
        """Get a list of Shade objects from the extruded border of this aperture.

        Args:
            depth: A number for the extrusion depth.
            indoor: Boolean for whether the extrusion should be generated facing the
                opposite direction of the aperture normal (typically meaning
                indoor geometry). Default: False.

        Returns:
            extrusion: A list of Shade objects for the extruded border.
        """
        extru_vec = self.normal if indoor is False else self.normal.reverse()
        extru_vec = extru_vec * depth
        extrusion = []
        shd_count = 0
        for seg in self.geometry.boundary_segments:
            shade_geo = Face3D.from_extrusion(seg, extru_vec)
            extrusion.append(
                Shade('{}_Shd{}'.format(self.name_original, shd_count), shade_geo))
            shd_count += 1
        if self.geometry.has_holes:
            for hole in self.geometry.hole_segments:
                for seg in hole:
                    shade_geo = Face3D.from_extrusion(seg, extru_vec)
                    extrusion.append(
                        Shade('{}_Shd{}'.format(self.name_original, shd_count),
                              shade_geo))
                    shd_count += 1
        return extrusion

    def louvers_by_number(self, louver_count, depth, offset=0, angle=0,
                          contour_vector=Vector3D(0, 0, 1), flip_start_side=False,
                          indoor=False, tolerance=0):
        """Get a list of louvered Shade objects covering this Aperture.

        Args:
            louver_count: A positive integer for the number of louvers to generate.
            depth: A number for the depth to extrude the louvers.
            offset: A number for the distance to louvers from this aperture.
                Default is 0 for no offset.
            angle: A number for the for an angle to rotate the louvers in degrees.
                Default is 0 for no rotation.
            contour_vector: A Vector3D for the direction along which contours
                are generated. Default is Z-Axis, which generates horizontal louvers.
            flip_start_side: Boolean to note whether the side the louvers start from
                should be flipped. Default is False to have louvers on top or right.
                Setting to True will start contours on the bottom or left.
            indoor: Boolean for whether louvers should be generated facing the
                opposite direction of the aperture normal (typically meaning
                indoor geometry). Default: False.
            tolerance: An optional value to remove any louvers with a length less
                than the tolerance. Default is 0, which will include all louvers
                no matter how small.

        Returns:
            louvers: A list of Shade objects that cover the Aperture.
        """
        assert louver_count > 0, 'louver_count must be greater than 0.'
        angle = math.radians(angle)
        louvers = []
        ap_geo = self.geometry if indoor is False else self.geometry.flip()
        shade_faces = ap_geo.countour_fins_by_number(
            louver_count, depth, offset, angle,
            contour_vector, flip_start_side, tolerance)
        for i, shade_geo in enumerate(shade_faces):
            louvers.append(Shade('{}_Shd{}'.format(self.name_original, i), shade_geo))
        return louvers

    def louvers_by_distance_between(self, distance, depth, offset=0, angle=0,
                                    contour_vector=Vector3D(0, 0, 1),
                                    flip_start_side=False, indoor=False, tolerance=0):
        """Get a list of louvered Shade objects covering this Aperture.

        Args:
            distance: A number for the approximate distance between each louver.
            depth: A number for the depth to extrude the louvers.
            offset: A number for the distance to louvers from this aperture.
                Default is 0 for no offset.
            angle: A number for the for an angle to rotate the louvers in degrees.
                Default is 0 for no rotation.
            contour_vector: A Vector3D for the direction along which contours
                are generated. Default is Z-Axis, which generates horizontal louvers.
            flip_start_side: Boolean to note whether the side the louvers start from
                should be flipped. Default is False to have contours on top or right.
                Setting to True will start contours on the bottom or left.
            indoor: Boolean for whether louvers should be generated facing the
                opposite direction of the aperture normal (typically meaning
                indoor geometry). Default: False.
            tolerance: An optional value to remove any louvers with a length less
                than the tolerance. Default is 0, which will include all louvers
                no matter how small.

        Returns:
            louvers: A list of Shade objects that cover the Aperture.
        """
        angle = math.radians(angle)
        louvers = []
        ap_geo = self.geometry if indoor is False else self.geometry.flip()
        shade_faces = ap_geo.countour_fins_by_distance_between(
            distance, depth, offset, angle,
            contour_vector, flip_start_side, tolerance)
        for i, shade_geo in enumerate(shade_faces):
            louvers.append(Shade('{}_Shd{}'.format(self.name_original, i), shade_geo))
        return louvers

    def move(self, moving_vec):
        """Move this Aperture along a vector.

        Args:
            moving_vec: A ladybug_geometry Vector3D with the direction and distance
                to move the face.
        """
        self._geometry = self.geometry.move(moving_vec)

    def rotate(self, axis, angle, origin):
        """Rotate this Aperture by a certain angle around an axis and origin.

        Args:
            axis: A ladybug_geometry Vector3D axis representing the axis of rotation.
            angle: An angle for rotation in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        self._geometry = self.geometry.rotate(axis, math.radians(angle), origin)

    def rotate_xy(self, angle, origin):
        """Rotate this Aperture counterclockwise in the world XY plane by a certain angle.

        Args:
            angle: An angle in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        self._geometry = self.geometry.rotate_xy(math.radians(angle), origin)

    def reflect(self, plane):
        """Reflect this Aperture across a plane with the input normal vector and origin.

        Args:
            plane: A ladybug_geometry Plane across which the object will
                be reflected.
        """
        assert isinstance(plane, Plane), \
            'Expected ladybug_geometry Plane. Got {}.'.format(type(plane))
        self._geometry = self.geometry.reflect(plane.n, plane.o)

    def scale(self, factor, origin=None):
        """Scale this Aperture by a factor from an origin point.

        Args:
            factor: A number representing how much the object should be scaled.
            origin: A ladybug_geometry Point3D representing the origin from which
                to scale. If None, it will be scaled from the World origin (0, 0, 0).
        """
        self._geometry = self.geometry.scale(factor, origin)

    def check_planar(self, tolerance, raise_exception=True):
        """Check whether all of the Aperture's vertices lie within the same plane.

        Args:
            tolerance: The minimum distance between a given vertex and a the
                object's's plane at which the vertex is said to lie in the plane.
            raise_exception: Boolean to note whether an ValueError should be
                raised if a vertex does not lie within the object's plane.
        """
        try:
            return self.geometry.validate_planarity(tolerance, raise_exception)
        except ValueError as e:
            raise ValueError('Aperture "{}" is not planar.\n{}'.format(
                self.name_original, e))

    def check_self_intersecting(self, raise_exception=True):
        """Check whether the edges of the Aperture intersect one another (like a bowtwie)

        Args:
            raise_exception: If True, a ValueError will be raised if the object
                intersects with itself. Default: True.
        """
        if self.geometry.is_self_intersecting:
            if raise_exception:
                raise ValueError('Aperture "{}" has self-intersecting edges.'.format(
                    self.name_original))
            return False
        return True

    def check_non_zero(self, tolerance=0.0001, raise_exception=True):
        """Check whether the area of the Aperture is above a certain "zero" tolerance.

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
                    'Aperture "{}" geometry is too small. Area must be at least {}. '
                    'Got {}.'.format(self.name_original, tolerance, self.area))
            return False
        return True

    @property
    def properties(self):
        """Aperture properties, including Radiance, Energy and other properties."""
        return self._properties

    @property
    def to(self):
        """Aperture writer object.

        Use this method to access Writer class to write the aperture in other formats.

        Usage:
            aperture.to.idf(aperture) -> idf string.
            aperture.to.radiance(aperture) -> Radiance string.
        """
        raise NotImplementedError('Aperture does not yet support writing to files.')
        return writer

    def to_dict(self, abridged=False, included_prop=None):
        """Return Aperture as a dictionary.

        Args:
            abridged: Boolean to note whether the full dictionary describing the
                object should be returned (False) or just an abridged version (True).
                Default: False.
            included_prop: List of properties to filter keys that must be included in
                output dictionary. For example ['energy'] will include 'energy' key if
                available in properties to_dict. By default all the keys will be
                included. To exclude all the keys from plugins use an empty list.
        """
        base = {
            'type': self.__class__.__name__,
            'name': self.name,
            'name_original': self.name_original,
            'geometry': self._geometry.to_dict(),
            'aperture_type': self.type.to_dict(),
            'properties': self.properties.to_dict(abridged, included_prop)
        }
        if 'energy' in base['properties']:
            base['boundary_condition'] = self.boundary_condition.to_dict(full=True)
        else:
            base['boundary_condition'] = self.boundary_condition.to_dict(full=False)
        if self.parent:
            base['parent'] = self.parent.name
        else:
            base['parent'] = None
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def ToString(self):
        return self.__repr__()

    def __copy__(self):
        new_ap = Aperture(self.name_original, self.geometry, self.type,
                          self.boundary_condition)
        new_ap._properties.duplicate_extension_attr(self._properties)
        return new_ap

    def __repr__(self):
        return 'Aperture: %s' % self.name_original
