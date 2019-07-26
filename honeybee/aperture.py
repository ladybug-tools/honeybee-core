# coding: utf-8
"""Honeybee Aperture."""
from ._basewithshade import _BaseWithShade
from .properties import ApertureProperties
from .aperturetype import aperture_types
from .boundarycondition import boundary_conditions, Outdoors, Surface
from .shade import Shade
import honeybee.writer as writer

from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.face import Face3D

import math


class Aperture(_BaseWithShade):
    """A single planar Aperture in a Face.

    Properties:
        name
        display_name
        type
        boundary_condition
        indoor_shades
        outdoor_shades
        parent
        has_parent
        geometry
        vertices
        upper_left_vertices
        triangulated_mesh3d
        normal
        center
        area
        perimeter
    """
    TYPES = aperture_types
    __slots__ = ('_geometry', '_parent', '_type', '_boundary_condition')

    def __init__(self, name, geometry, type=None, boundary_condition=None):
        """A single planar aperture in a face.

        Args:
            name: Aperture name. Must be < 100 characters.
            geometry: A ladybug-geometry Face3D.
            type: Aperture type. Default: Window
            boundary_condition: Boundary condition object (Outdoors, Surface).
                Default: Outdoors.
        """
        _BaseWithShade.__init__(self, name)  # process the name

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
    def from_dict(cls, data):
        """Initialize an Aperture from a dictionary.

        Args:
            data: A dictionary representation of an Aperture object.
        """
        # check the type of dictionary
        assert data['type'] == 'Aperture', 'Expected Aperture dictionary. ' \
            'Got {}.'.format(data['type'])

        ap_type = aperture_types.by_name(data['aperture_type'])
        if data['boundary_condition']['type'] == 'Outdoors':
            boundary_condition = Outdoors.from_dict(data['boundary_condition'])
        elif data['boundary_condition']['type'] == 'Surface':
            boundary_condition = Surface.from_dict(data['boundary_condition'], True)
        else:
            raise ValueError(
                'Boundary condition "{}" is not supported for Apertures.'.format(
                    data['boundary_condition']['type']))
        aperture = cls(data['name'], Face3D.from_dict(data['geometry']),
                       ap_type, boundary_condition)
        if 'display_name' in data and data['display_name'] is not None:
            aperture._display_name = data['display_name']
        aperture._recover_shades_from_dict(data)
        return aperture

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
    def type(self):
        """Object for Type of Aperture (ie. Window)."""
        return self._type

    @type.setter
    def type(self, value):
        assert value in self.TYPES, '{} is not a valid aperture type.'.format(value)
        self._type = value

    @property
    def boundary_condition(self):
        """Boundary condition of this aperture."""
        return self._boundary_condition

    @boundary_condition.setter
    def boundary_condition(self, value):
        if not isinstance(value, Outdoors):
            if isinstance(value, Surface):
                assert len(value.boundary_condition_objects) == 3, 'Surface boundary ' \
                    'condition for Aperture must have 3 boundary_condition_objects.'
            else:
                raise ValueError('Aperture only supports Outdoor or Surface boundary '
                                 'condition. Got {}'.format(type(value)))
        self._boundary_condition = value

    @property
    def parent(self):
        """Parent Face if assigned. None if not assigned."""
        return self._parent

    @property
    def has_parent(self):
        """Boolean noting whether this Aperture has a parent Face."""
        return self._parent is not None

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
        self._boundary_condition = boundary_conditions.surface(other_aperture, True)
        other_aperture._boundary_condition = boundary_conditions.surface(self, True)

    def overhang(self, depth, angle=0, indoor=False, tolerance=0, base_name=None):
        """Add a single overhang for this Aperture.

        Args:
            depth: A number for the overhang depth.
            angle: A number for the for an angle to rotate the overhang in degrees.
                Default is 0 for no rotation.
            indoor: Boolean for whether the overhang should be generated facing the
                opposite direction of the aperture normal (typically meaning
                indoor geometry). Default: False.
            tolerance: An optional value to return None if the overhang has a length less
                than the tolerance. Default is 0, which will always yeild an overhang.
            base_name: Optional base name for the shade objects. If None, the default
                is InOverhang or OutOverhang depending on whether indoor is True.
        """
        if base_name is None:
            base_name = 'InOverhang' if indoor else 'OutOverhang'
        self.louvers_by_number(1, depth, angle=angle, indoor=indoor,
                               tolerance=tolerance, base_name=base_name)

    def right_fin(self, depth, angle=0, indoor=False, tolerance=0, base_name=None):
        """Add a single vertical fin on the right side of this Aperture.

        Args:
            depth: A number for the fin depth.
            angle: A number for the for an angle to rotate the fin in degrees.
                Default is 0 for no rotation.
            indoor: Boolean for whether the fin should be generated facing the
                opposite direction of the aperture normal (typically meaning
                indoor geometry). Default: False.
            tolerance: An optional value to return None if the fin has a length less
                than the tolerance. Default is 0, which will always yeild a fin.
            base_name: Optional base name for the shade objects. If None, the default
                is InRightFin or OutRightFin depending on whether indoor is True.
        """
        if base_name is None:
            base_name = 'InRightFin' if indoor else 'OutRightFin'
        self.louvers_by_number(1, depth, angle=angle, contour_vector=Vector3D(1, 0, 0),
                               indoor=indoor, tolerance=tolerance, base_name=base_name)

    def left_fin(self, depth, angle=0, indoor=False, tolerance=0, base_name=None):
        """Add a single vertical fin on the left side of this Aperture.

        Args:
            depth: A number for the fin depth.
            angle: A number for the for an angle to rotate the fin in degrees.
                Default is 0 for no rotation.
            indoor: Boolean for whether the fin should be generated facing the
                opposite direction of the aperture normal (typically meaning
                indoor geometry). Default: False.
            tolerance: An optional value to return None if the fin has a length less
                than the tolerance. Default is 0, which will always yeild a fin.
            base_name: Optional base name for the shade objects. If None, the default
                is InLeftFin or OutLeftFin depending on whether indoor is True.
        """
        if base_name is None:
            base_name = 'InLeftFin' if indoor else 'OutLeftFin'
        self.louvers_by_number(1, depth, angle=angle, contour_vector=Vector3D(1, 0, 0),
                               flip_start_side=True, indoor=indoor,
                               tolerance=tolerance, base_name=base_name)

    def extruded_border(self, depth, indoor=False, base_name=None):
        """Add a series of Shade objects to this Aperture that form an extruded border.

        Args:
            depth: A number for the extrusion depth.
            indoor: Boolean for whether the extrusion should be generated facing the
                opposite direction of the aperture normal (typically meaning
                indoor geometry). Default: False.
            base_name: Optional base name for the shade objects. If None, the default
                is InBorder or OutBorder depending on whether indoor is True.
        """
        extru_vec = self.normal if indoor is False else self.normal.reverse()
        extru_vec = extru_vec * depth
        extrusion = []
        shd_count = 0
        if base_name is None:
            shd_name_base = '{}_InBorder{}' if indoor else '{}_OutBorder{}'
        else:
            shd_name_base = '{}_' + str(base_name) + '{}'
        for seg in self.geometry.boundary_segments:
            shade_geo = Face3D.from_extrusion(seg, extru_vec)
            extrusion.append(
                Shade(shd_name_base.format(self.display_name, shd_count), shade_geo))
            shd_count += 1
        if self.geometry.has_holes:
            for hole in self.geometry.hole_segments:
                for seg in hole:
                    shade_geo = Face3D.from_extrusion(seg, extru_vec)
                    extrusion.append(
                        Shade(shd_name_base.format(self.display_name, shd_count),
                              shade_geo))
                    shd_count += 1
        if indoor:
            self._indoor_shades.extend(extrusion)
        else:
            self._outdoor_shades.extend(extrusion)

    def louvers_by_number(self, louver_count, depth, offset=0, angle=0,
                          contour_vector=Vector3D(0, 0, 1), flip_start_side=False,
                          indoor=False, tolerance=0, base_name=None):
        """Add a series of louvered Shade objects covering this Aperture.

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
            base_name: Optional base name for the shade objects. If None, the default
                is InShd or OutShd depending on whether indoor is True.
        """
        assert louver_count > 0, 'louver_count must be greater than 0.'
        angle = math.radians(angle)
        louvers = []
        ap_geo = self.geometry if indoor is False else self.geometry.flip()
        shade_faces = ap_geo.countour_fins_by_number(
            louver_count, depth, offset, angle,
            contour_vector, flip_start_side, tolerance)
        if base_name is None:
            shd_name_base = '{}_InShd{}' if indoor else '{}_OutShd{}'
        else:
            shd_name_base = '{}_' + str(base_name) + '{}'
        for i, shade_geo in enumerate(shade_faces):
            louvers.append(Shade(shd_name_base.format(self.display_name, i), shade_geo))
        if indoor:
            self._indoor_shades.extend(louvers)
        else:
            self._outdoor_shades.extend(louvers)

    def louvers_by_distance_between(
            self, distance, depth, offset=0, angle=0, contour_vector=Vector3D(0, 0, 1),
            flip_start_side=False, indoor=False, tolerance=0, base_name=None):
        """Add a series of louvered Shade objects covering this Aperture.

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
            base_name: Optional base name for the shade objects. If None, the default
                is InShd or OutShd depending on whether indoor is True.
        """
        angle = math.radians(angle)
        louvers = []
        ap_geo = self.geometry if indoor is False else self.geometry.flip()
        shade_faces = ap_geo.countour_fins_by_distance_between(
            distance, depth, offset, angle,
            contour_vector, flip_start_side, tolerance)
        if base_name is None:
            shd_name_base = '{}_InShd{}' if indoor else '{}_OutShd{}'
        else:
            shd_name_base = '{}_' + str(base_name) + '{}'
        for i, shade_geo in enumerate(shade_faces):
            louvers.append(Shade(shd_name_base.format(self.display_name, i), shade_geo))
        if indoor:
            self._indoor_shades.extend(louvers)
        else:
            self._outdoor_shades.extend(louvers)

    def move(self, moving_vec):
        """Move this Aperture along a vector.

        Args:
            moving_vec: A ladybug_geometry Vector3D with the direction and distance
                to move the face.
        """
        self._geometry = self.geometry.move(moving_vec)
        self.move_shades(moving_vec)

    def rotate(self, axis, angle, origin):
        """Rotate this Aperture by a certain angle around an axis and origin.

        Args:
            axis: A ladybug_geometry Vector3D axis representing the axis of rotation.
            angle: An angle for rotation in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        self._geometry = self.geometry.rotate(axis, math.radians(angle), origin)
        self.rotate_shades(axis, angle, origin)

    def rotate_xy(self, angle, origin):
        """Rotate this Aperture counterclockwise in the world XY plane by a certain angle.

        Args:
            angle: An angle in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        self._geometry = self.geometry.rotate_xy(math.radians(angle), origin)
        self.rotate_xy_shades(angle, origin)

    def reflect(self, plane):
        """Reflect this Aperture across a plane.

        Args:
            plane: A ladybug_geometry Plane across which the object will
                be reflected.
        """
        self._geometry = self.geometry.reflect(plane.n, plane.o)
        self.reflect_shades(plane)

    def scale(self, factor, origin=None):
        """Scale this Aperture by a factor from an origin point.

        Args:
            factor: A number representing how much the object should be scaled.
            origin: A ladybug_geometry Point3D representing the origin from which
                to scale. If None, it will be scaled from the World origin (0, 0, 0).
        """
        self._geometry = self.geometry.scale(factor, origin)
        self.scale_shades(factor, origin)

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
                self.display_name, e))

    def check_self_intersecting(self, raise_exception=True):
        """Check whether the edges of the Aperture intersect one another (like a bowtwie)

        Args:
            raise_exception: If True, a ValueError will be raised if the object
                intersects with itself. Default: True.
        """
        if self.geometry.is_self_intersecting:
            if raise_exception:
                raise ValueError('Aperture "{}" has self-intersecting edges.'.format(
                    self.display_name))
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
                    'Got {}.'.format(self.display_name, tolerance, self.area))
            return False
        return True

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
            abridged: Boolean to note whether the extension properties of the
                object (ie. materials, construcitons) should be included in detail
                (False) or just referenced by name (True). Default: False.
            included_prop: List of properties to filter keys that must be included in
                output dictionary. For example ['energy'] will include 'energy' key if
                available in properties to_dict. By default all the keys will be
                included. To exclude all the keys from extensions use an empty list.
        """
        base = {'type': 'Aperture'}
        base['name'] = self.name
        base['display_name'] = self.display_name
        base['properties'] = self.properties.to_dict(abridged, included_prop)

        if 'energy' in base['properties']:
            base['geometry'] = self._geometry.to_dict(False, True)  # enforce upper-left
        else:
            base['geometry'] = self._geometry.to_dict(False)

        base['aperture_type'] = self.type.name
        if isinstance(self.boundary_condition, Outdoors) and 'energy' in base['properties']:
            base['boundary_condition'] = self.boundary_condition.to_dict(full=True)
        else:
            base['boundary_condition'] = self.boundary_condition.to_dict()
        self._add_shades_to_dict(base, abridged, included_prop)
        return base

    def __copy__(self):
        new_ap = Aperture(self.name, self.geometry, self.type, self.boundary_condition)
        new_ap._display_name = self.display_name
        self._duplicate_child_shades(new_ap)
        new_ap._properties.duplicate_extension_attr(self._properties)
        return new_ap

    def __repr__(self):
        return 'Aperture: %s' % self.display_name
