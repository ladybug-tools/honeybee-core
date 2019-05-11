"""Energy Types."""


class _FaceType(object):
    @property
    def name(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.name


class Wall(_FaceType):
    pass


class RoofCeiling(_FaceType):
    pass


class Floor(_FaceType):
    pass


class AirWall(_FaceType):
    pass


class Shading(_FaceType):
    pass


class Types(object):
    """Face types."""

    def __init__(self):
        pass

    @property
    def wall(self):
        return Wall()

    @property
    def roof_ceiling(self):
        return RoofCeiling()

    @property
    def floor(self):
        return Floor()

    @property
    def airwall(self):
        return AirWall()

    @property
    def shading(self):
        return Shading()

    def __contains__(self, value):
        return isinstance(value, _FaceType)
