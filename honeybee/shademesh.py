# coding: utf-8
"""Honeybee ShadeMesh."""
from __future__ import division
import math

from ladybug_geometry.geometry3d import Mesh3D, Face3D
from ladybug.color import Color

from ._base import _Base
from .typing import clean_string
from .properties import ShadeMeshProperties
import honeybee.writer.shademesh as writer


class ShadeMesh(_Base):
    """A single planar shade.

    Args:
        identifier: Text string for a unique Shade ID. Must be < 100 characters and
            not contain any spaces or special characters.
        geometry: A ladybug-geometry Mesh3D.
        is_detached: Boolean to note whether this object is detached from other
            geometry. Cases where this should be True include shade representing
            surrounding buildings or context. (Default: True).

    Properties:
        * identifier
        * display_name
        * is_detached
        * geometry
        * vertices
        * faces
        * center
        * area
        * min
        * max
        * type_color
        * bc_color
        * user_data
    """
    __slots__ = ('_geometry', '_is_detached')
    TYPE_COLORS = {
        False: Color(120, 75, 190),
        True: Color(80, 50, 128)
    }
    BC_COLOR = Color(120, 75, 190)

    def __init__(self, identifier, geometry, is_detached=True):
        """A single planar shade."""
        _Base.__init__(self, identifier)  # process the identifier

        # process the geometry and basic properties
        assert isinstance(geometry, Mesh3D), \
            'Expected ladybug_geometry Mesh3D. Got {}'.format(type(geometry))
        self._geometry = geometry
        self.is_detached = is_detached

        # initialize properties for extensions
        self._properties = ShadeMeshProperties(self)

    @classmethod
    def from_dict(cls, data):
        """Initialize an ShadeMesh from a dictionary.

        Args:
            data: A dictionary representation of an ShadeMesh object.
        """
        try:
            # check the type of dictionary
            assert data['type'] == 'ShadeMesh', 'Expected ShadeMesh dictionary. ' \
                'Got {}.'.format(data['type'])

            is_detached = data['is_detached'] if 'is_detached' in data else True
            shade = cls(
                data['identifier'], Mesh3D.from_dict(data['geometry']), is_detached)
            if 'display_name' in data and data['display_name'] is not None:
                shade.display_name = data['display_name']
            if 'user_data' in data and data['user_data'] is not None:
                shade.user_data = data['user_data']

            if data['properties']['type'] == 'ShadeMeshProperties':
                shade.properties._load_extension_attr_from_dict(data['properties'])
            return shade
        except Exception as e:
            cls._from_dict_error_message(data, e)

    @property
    def is_detached(self):
        """Get or set a boolean for whether this object is detached from other geometry.
        """
        return self._is_detached

    @is_detached.setter
    def is_detached(self, value):
        try:
            self._is_detached = bool(value)
        except TypeError:
            raise TypeError(
                'Expected boolean for ShadeMesh.is_detached. Got {}.'.format(value))

    @property
    def geometry(self):
        """Get a ladybug_geometry Mesh3D object representing the Shade."""
        return self._geometry

    @property
    def vertices(self):
        """Get a tuple of ladybug_geometry Point3D for the vertices of the mesh."""
        return self._geometry.vertices

    @property
    def faces(self):
        """Get a tuple of tuples for the faces of the mesh."""
        return self._geometry.faces

    @property
    def center(self):
        """Get a ladybug_geometry Point3D for the center of the shade.

        Note that this is the center of the bounding box around this geometry
        and not the area or volume centroid.
        """
        return self._geometry.center

    @property
    def area(self):
        """Get the surface area of the shade mesh."""
        return self._geometry.area

    @property
    def min(self):
        """Get a Point3D for the minimum of the bounding box around the object."""
        return self._geometry.min

    @property
    def max(self):
        """Get a Point3D for the maximum of the bounding box around the object."""
        return self._geometry.max

    @property
    def type_color(self):
        """Get a Color to be used in visualizations by type."""
        return self.TYPE_COLORS[self.is_detached]

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

    def triangulate_and_remove_degenerate_faces(self, tolerance=0.01):
        """Triangulate non-planar faces in the mesh and remove all degenerate faces.

        This is helpful for certain geometry interfaces that require perfectly
        planar geometry without duplicate or colinear vertices.

        Args:
            tolerance: The minimum distance between a vertex and the boundary segments
                at which point the vertex is considered colinear. Default: 0.01,
                suitable for objects in meters.
        """
        new_faces, verts = [], self.geometry.vertices
        for shd in self.faces:
            shd_verts = [verts[v] for v in shd]
            shf = Face3D(shd_verts)
            if len(shd_verts) == 4 and not \
                    shf.check_planar(tolerance, raise_exception=False):
                shades = ((shd[0], shd[1], shd[2]), (shd[2], shd[3], shd[0]))
                for shade in shades:
                    shd_verts = [verts[v] for v in shade]
                    shade_face = Face3D(shd_verts)
                    try:
                        shade_face.remove_colinear_vertices(tolerance)
                    except AssertionError:
                        continue  # degenerate face to remove
                    new_faces.append(shade)
            else:
                try:
                    new_face = shf.remove_colinear_vertices(tolerance)
                except AssertionError:
                    continue  # degenerate face to remove
                if len(new_face.vertices) == len(shd):
                    new_faces.append(shd)
                else:  # quad face with duplicate or colinear verts
                    new_sh = tuple(shd[shd_verts.index(v)] for v in new_face.vertices)
                    new_faces.append(new_sh)
        self._geometry = Mesh3D(verts, new_faces)

    def is_geo_equivalent(self, shade_mesh, tolerance=0.01):
        """Get a boolean for whether this object is geometrically equivalent to another.

        The total number of vertices and the ordering of these vertices can be
        different but the geometries must share the same center point and be
        next to one another to within the tolerance.

        Args:
            shade_mesh: Another ShadeMesh for which geometric equivalency will be tested.
            tolerance: The minimum difference between the coordinate values of two
                vertices at which they can be considered geometrically equivalent.

        Returns:
            True if geometrically equivalent. False if not geometrically equivalent.
        """
        meta_1 = (self.display_name, self.is_detached)
        meta_2 = (shade_mesh.display_name, shade_mesh.is_detached)
        if meta_1 != meta_2:
            return False
        if len(self.geometry.vertices) != len(shade_mesh.geometry.vertices):
            return False
        if len(self.geometry.faces) != len(shade_mesh.geometry.faces):
            return False
        return all(pt.is_equivalent(o_pt, tolerance) for pt, o_pt in
                   zip(self.geometry.vertices, shade_mesh.geometry.vertices))

    def display_dict(self):
        """Get a list of DisplayMesh3D dictionaries for visualizing the object."""
        return [self._display_mesh(self.geometry, self.type_color)]

    @property
    def to(self):
        """ShadeMesh writer object.

        Use this method to access Writer class to write the shade in different formats.

        Usage:

        .. code-block:: python

            shade_mesh.to.idf(shade) -> idf string.
            shade_mesh.to.radiance(shade) -> Radiance string.
        """
        return writer

    def to_dict(self, abridged=False, included_prop=None):
        """Return Shade as a dictionary.

        Args:
            abridged: Boolean to note whether the extension properties of the
                object (ie. modifiers, transmittance schedule) should be included in
                detail (False) or just referenced by identifier (True). Default: False.
            included_prop: List of properties to filter keys that must be included in
                output dictionary. For example ['energy'] will include 'energy' key if
                available in properties to_dict. By default all the keys will be
                included. To exclude all the keys from extensions use an empty list.
        """
        base = {'type': 'ShadeMesh'}
        base['identifier'] = self.identifier
        base['display_name'] = self.display_name
        base['properties'] = self.properties.to_dict(abridged, included_prop)
        base['geometry'] = self._geometry.to_dict()
        if not self.is_detached:
            base['is_detached'] = self.is_detached
        if self.user_data is not None:
            base['user_data'] = self.user_data
        return base

    @staticmethod
    def _display_mesh(mesh3d, color):
        """Create a DisplayMesh3D dictionary from a Mesh3D and color."""
        return {
            'type': 'DisplayMesh3D',
            'geometry': mesh3d.to_dict(),
            'color': color.to_dict(),
            'display_mode': 'SurfaceWithEdges'
        }

    def __copy__(self):
        new_shade = ShadeMesh(self.identifier, self.geometry, self.is_detached)
        new_shade._display_name = self._display_name
        new_shade._user_data = None if self.user_data is None else self.user_data.copy()
        new_shade._properties._duplicate_extension_attr(self._properties)
        return new_shade

    def __repr__(self):
        return 'ShadeMesh: %s' % self.display_name
