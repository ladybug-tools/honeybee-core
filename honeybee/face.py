# coding: utf-8
"""Honeybee Face."""
from .properties import Properties
from .facetype import get_type_from_normal
import honeybee.writer as writer
from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.geometry3d.pointvector import Point3D

import re
import weakref


class Face(object):
    """A single planar face."""

    def __init__(self, name, geometry, face_type=None, boundary_condition=None):
        """A single planar face.
        Args:
            name: Face name.
            geometry: A ladybug-geometry Face3D.
            face_type: Face type (e.g. wall, floor).
            boundary_condition: Face boundary condition (Outdoors, Ground, etc.)
        """
        self.name = name
        assert isinstance(geometry, Face3D), \
            'Expected ladybug_geometry Face3D not {}'.format(type(geometry))
        self._geometry = geometry
        # _parent will be set when the Face is added to a Zone
        # in case of aperture it will be added when aperture is added to a Face.
        self._parent = None
        # get face type based on normal if face_type is not provided
        face_type = face_type or get_type_from_normal(geometry.normal)
        self._properties = Properties(face_type, boundary_condition)
        self._writer = writer
        self._apertures = []

    @property
    def name(self):
        """Face name."""
        return self._name

    @name.setter
    def name(self, value):
        self._name = re.sub(r'[^.A-Za-z0-9_-]', '', value)
        self._name_original = value

    @property
    def name_original(self):
        """Original input name by user.

        If there is no illegal characters in name then name and name_original will be the
        same. Legal characters are ., A-Z, a-z, 0-9, _ and -. Invalid characters are
        removed from the original name for compatability with simulation engines.
        """
        return self._name_original

    @property
    def vertices(self):
        """List of vertices."""
        return self._geometry.vertices

    @property
    def face_type(self):
        """Face type."""
        return self._properties.face_type

    @face_type.setter
    def face_type(self, f_type):
        self._properties.face_type = f_type

    @property
    def boundary_condition(self):
        """Face type."""
        return self._properties.boundary_condition

    @boundary_condition.setter
    def boundary_condition(self, bc):
        self._properties.boundary_condition = bc
    
    @property
    def apertures(self):
        """List of apertures."""
        return self._apertures

    @property
    def parent(self):
        """Parent zone."""
        return self._parent

    @classmethod
    def from_vertices(cls, name, vertices, face_type=None, boundary_condition=None):
        """Create a Face from vertices.

        args:
            name: Face name.
            vertices: A flattened list of 3 or more vertices as (x, y, z).
            face_type: Face type (e.g. wall, floor).
        """
        geometry = Face3D([Point3D(*v) for v in vertices])
        return cls(name, geometry, face_type, boundary_condition)

    @property
    def properties(self):
        """Face properties.

        Radiance, energy and other face properties.
        """
        return self._properties

    @property
    def to(self):
        """Face writer object.

        Use this method to access Writer class to write the face in different formats.

        face.to.idf(face) -> idf string.
        face.to.radiance(face) -> Radiance string.
        """
        return self._writer

    def to_dict(self, included_prop=None):
        """Return Face as a dictionary.
        
        args:
            included_prop: Use properties filter to filter keys that must be included in
            output dictionary. For example ['energy'] will include 'energy' key if
            available in properties to_dict. By default all the keys will be included.
            To exclude all the keys from plugins use an empty list.
        """
        base = {
            'type': self.__class__.__name__,
            'name': self.name,
            'name_original': self.name_original,
            'vertices': [{'x': ver.x, 'y': ver.y, 'z': ver.z} for ver in self.vertices],
            'properties': self.properties.to_dict(included_prop)
        }

        if self.parent:
            base['parent'] = {'name': self.parent.name}

        if self.apertures:
            base['apertures'] = [ap.to_dict(included_prop) for ap in self.apertures]

        return base


    def add_aperture(self, aperture):
        """Add an aperture to face."""
        aperture._parent = self
        self._apertures.append(weakref.proxy(aperture))

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'Face:%s' % self.name_original
