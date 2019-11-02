# coding: utf-8
"""Base class for all geometry objects."""
from .typing import valid_string


class _Base(object):
    """A base class for all geometry objects.

    Properties:
        name
        display_name
    """
    __slots__ = ('_name', '_display_name', '_properties')

    def __init__(self, name):
        """Initialize base object.

        Args:
            name: Object name. Must be < 100 characters.
        """
        self.name = name
        self._properties = None

    @property
    def name(self):
        """Get or set the object name (including only legal characters)."""
        return self._name

    @name.setter
    def name(self, value):
        self._name = valid_string(value, 'honeybee object name')
        self._display_name = value

    @property
    def display_name(self):
        """Get the original input name by user.

        If there are no illegal characters in name then name and display_name will
        be the same. Legal characters are ., A-Z, a-z, 0-9, _ and -.
        Invalid characters are automatically removed from the original name for
        compatability with simulation engines.
        """
        return self._display_name

    @property
    def properties(self):
        """Get object properties, including Radiance, Energy and other properties."""
        return self._properties
    
    def rename(self, prefix):
        """Change the name of this object by inserting a prefix.
        
        This is particularly useful in workflows where you duplicate and edit
        a starting object and then want to combine it with the original object
        into one Model (like making a model of repeated rooms) since all objects
        within a Model must have unique names.

        Args:
            prefix: Text that will be inserted at the start of this object's name
                and display_name. It is recommended that this name be short to
                avoid maxing out the 100 allowable characters for honeybee names.
        """
        self.name = '{}{}'.format(prefix, self.display_name)

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        new_obj = self.__class__(self.name)
        new_obj._display_name = self.display_name
        return new_obj

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'Honeybee Base Object: %s' % self.display_name
