"""Geometry Writer.

Note for developers:

Use this class to extend honeybee's geometry writer for new plugins.
"""


class Writer(object):
    """Writer class.
    
    This class is a place holder for adding writers from new plugins. See
    honeybee_energy._extend_honeybee for an example.
    """

    def __init__(self, geo_type, name, vertices, parent, properties):
        """Writer."""
        self.geo_type = geo_type  # Face, PolyFace, etc
        self.name = name
        self.vertices = vertices
        self.parent = parent
        self.properties = properties
    
    def __repr__(self):
        return 'FaceWriter'
