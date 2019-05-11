# coding: utf-8
"""Honeybee Face."""
from .geoparser import GeoParser
from .properties import Properties
from .writer import Writer

import re


class Face(object):
    """A single planar face."""

    def __init__(self, name, vertices, face_type=None):
        """A single planar face.
        Args:
            name: Face name.
            vertices: A flattened list of 3 or more vertices.
            face_type: Face type (e.g. wall, floor).

        """
        self.name = name
        self._vertices = vertices
        self._properties = Properties(face_type)
        self._writer = Writer(
            self.__class__.__name__, self.name, self.vertices, self.properties
        )

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
        return self._vertices

    @property
    def face_type(self):
        """Face type."""
        return self._properties.face_type

    @classmethod
    def from_geometry(cls, geometry, source, face_type=None, parameters=None):
        """Create a Face from a geometry.

        This method is useful for creating a face from Ladybug Tools plugins. You need
        to install the plugin library (e.g. honeybee_grasshopper or honeybee_dynamo)
        in order to use this method.

        args:
            geometry: Input geometry.
            source: Source software that is used to create this geometry
                (e.g. rhino, revit).
            parameters: Optional user parameters that can be used by parser.
        """
        geo_parser = GeoParser()
        try:
            parser = geo_parser.getattr(source.lower())
        except AttributeError:
            raise AttributeError(
                'Failed to find parser for {0}.\nDid you misspell the source name?'
                '\nIf the name is spelled correctly did you install honeybee_{0} '
                'library?'.format(source)
            )
        else:
            vertices = parser(geometry, parameters)
            return cls(vertices, face_type)

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

        face.to.radiance(face) -> Radiance string.
        """
        return self._writer
