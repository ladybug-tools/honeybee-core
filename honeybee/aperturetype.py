# coding=utf-8
"""Aperture Types."""
import re


class _ApertureType(object):
    __slots__ = ()

    def __init__(self):
        pass

    @property
    def name(self):
        return self.__class__.__name__

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


class _ApertureTypes(object):
    """Aperture types enumeration."""

    _window = Window()

    def __init__(self):
        pass

    @property
    def window(self):
        return self._window

    def by_name(self, aperture_type_name):
        """Get an Aperture Type instance from its name.

        Args:
            aperture_type_name: A text string for the aperture type (eg. "Window").
        """
        attr_name = re.sub('(?<!^)(?=[A-Z])', '_', aperture_type_name).lower()
        try:
            return getattr(self, attr_name)
        except AttributeError:
            raise AttributeError('Aperture Type "{}" is not supported by this '
                                 'installation of honeybee.'.format(aperture_type_name))

    def __contains__(self, value):
        return isinstance(value, _ApertureType)


aperture_types = _ApertureTypes()
