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


class _Types(object):
    """Face types."""

    def __init__(self):
        self._wall = Wall()
        self._roof_ceiling = RoofCeiling()
        self._floor = Floor()
        self._air_wall = AirWall()
        self._shading = Shading()

    @property
    def wall(self):
        return self._wall

    @property
    def roof_ceiling(self):
        return self._roof_ceiling

    @property
    def floor(self):
        return self._floor

    @property
    def airwall(self):
        return self._air_wall

    @property
    def shading(self):
        return self._shading

    def __contains__(self, value):
        return isinstance(value, _FaceType)


face_types = _Types()
