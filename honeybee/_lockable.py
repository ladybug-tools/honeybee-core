# coding=utf-8
"""Descriptor that for locking and unlocking an object, preventing attribute setting."""
from functools import wraps
from inspect import getmro


def lockable(cls):
    """A decorator for making lockable class.

    If a class is locked, attributes can no longer be set on the class.
    The class will throw an AttributeError if one tries to do so.

    Classes start out as unlocked but can be locked by calling the `lock()` method.
    If the class needs to be unlocked again, calling the `unlock()` method will
    unlock it and allow you to edit attributes on the class.  You can also create
    a class that starts out as locked by putting `self._locked = True` at the end
    of a class's `__init__` method.

    Note that classes using __slots__ must specify a '_locked' variable within
    the __slots__ in order to work correctly with this decorator.

    This example if modified from:
    http://stackoverflow.com/questions/3603502/prevent-creating-new-attributes-outside-init

    Usage:

    .. code-block:: python

        @lockable
        class Foo(object):
            def __init__(self):
                self.bar = 10

        foo = Foo()
        foo.bar = 20

        foo.lock()
        try:
            foo.bar = 30
        except AttributeError as e:
            print(e)
        > Failed to set bar to 30. bar cannot be set on Foo while it is locked.
          The unlock() method can unlock the class but you do so at your own risk.
          Objects are typically locked when they are referenced from many other objects.
          So it is usually better to make a new instance of Foo and proceed using that.

        foo.unlock()
        foo.bar = 30
        foo.lock()
    """

    def lockedsetattr(self, key, value):
        """Method to overwrite __setattr__ on the decorated class."""
        if hasattr(self, '_locked') and self._locked and not key == '_locked':
            raise AttributeError(
                'Failed to set {1} to {2}. {1} cannot be set on {0} while it is locked.'
                '\nThe unlock() method can unlock the class but you do so at '
                'your own risk.\nObjects are typically locked when they are referenced '
                'from several other objects.\n So it is usually better practice to'
                'make a new instance of {0} and proceed using that.'.format(
                    cls.__name__, key, value))
        else:
            object.__setattr__(self, key, value)

    def init_decorator(func):
        """Initialize the lockable decorator for the class."""

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            func(self, *args, **kwargs)
        return wrapper

    def lock(self):
        self._locked = True

    def unlock(self):
        self._locked = False

    # overwrite the various methods on the class to support lockability
    cls.__setattr__ = lockedsetattr
    cls.__init__ = init_decorator(cls.__init__)
    if not hasattr(cls, 'lock'):  # allow developers to add their own lock method
        cls.lock = lock
    if not hasattr(cls, 'unlock'):  # allow developers to add their own unlock method
        cls.unlock = unlock

    # if the class uses __slots__, check that _locked is somewhere in inheritance tree
    if hasattr(cls, '__slots__'):
        _all_good = False
        for parent_class in getmro(cls)[:-1]:
            if '_locked' in parent_class.__slots__:
                _all_good = True
                break
        if not _all_good:
            raise AttributeError(
                'When using the @lockable decorator on a class with __slots__, '
                'a "_locked" variable must be specified within __slots__.')

    return cls
