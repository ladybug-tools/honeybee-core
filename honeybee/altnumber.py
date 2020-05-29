"""Objects used as alternatives to various numerical properties."""


class _AltNumber(object):
    __slots__ = ()

    def __init__(self):
        pass

    @property
    def name(self):
        return self.__class__.__name__

    def to_dict(self):
        """Get the object as a dictionary."""
        return {'type': self.name}

    def ToString(self):
        return self.__repr__()

    def __eq__(self, other):
        return self.__class__ == other.__class__

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return self.name


class NoLimit(_AltNumber):
    """Object representing no limit to a certain numerical value."""
    __slots__ = ()
    pass


class Autocalculate(_AltNumber):
    """Object representing when a certain numerical value is automatically calculated.

    Typically, this means that the value is determined from other variables.
    """
    __slots__ = ()
    pass


no_limit = NoLimit()
autocalculate = Autocalculate()
