# coding=utf-8
"""Aperture Types."""


class _ApertureType(object):
    __slots__ = ()

    @property
    def name(self):
        return self.__class__.__name__

    def to_dict(self):
        """ApertureType as a dictionary."""
        ap_type_dict = {
            'type': self.name}
        return ap_type_dict

    def ToString(self):
        return self.__repr__()

    def __eq__(self, other):
        return self.__class__ == other.__class__

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return self.name


class Window(_ApertureType):
    """Type for static apertures that are not intended to be opened."""
    __slots__ = ()
    pass


class _Types(object):
    """Aperture types."""

    def __init__(self):
        self._window = Window()

    @property
    def window(self):
        return self._window

    def __contains__(self, value):
        return isinstance(value, _ApertureType)


aperture_types = _Types()
