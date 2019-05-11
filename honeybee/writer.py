"""Geometry Writer.

Note for developers:

Use this class to extend honeybee's geometry writer for new plugins.
"""


class Writer(object):
    """Writer class.
    
    This class is a place holder for adding writers from new plugins. See
    honeybee_radiance for an example.

    def radiance(self, face):
        # your code for generating radiance string.
        # keep in mind that vertices can be a list for Face or a list of list for
        # PolyFace 
        return rad_string
    """

    def __init__(self):
        """Writer."""
        pass
    
    def __repr__(self):
        return 'FaceWriter'
