"""Test locakble decorator."""
from honeybee._lockable import lockable

import pytest


def test_simple_class():
    """Test the application of the lockable decorator to a simple class."""
    @lockable
    class Foo(object):
        def __init__(self):
            self.bar = 10

    foo = Foo()
    foo.bar = 20

    foo.lock()
    with pytest.raises(AttributeError):
        foo.bar = 30

    foo.unlock()
    foo.bar = 30
    assert foo.bar == 30
    foo.lock()


def test_nested_classes():
    """Test lockable decorator with nested classes, which are not locked by default."""
    @lockable
    class Material(object):
        def __init__(self):
            self.r_value = 3

    @lockable
    class Construction(object):
        def __init__(self):
            self.material = Material()

    constr = Construction()
    constr.lock()
    with pytest.raises(AttributeError):
        constr.material = Material()

    constr.material.r_value = 5
    constr.material.lock()
    with pytest.raises(AttributeError):
        constr.material.r_value = 10


def test_custom_lock_method():
    """Test the lockable decorator with a custom lock() method to lock nested classes."""
    @lockable
    class Material(object):
        def __init__(self):
            self.r_value = 3

    @lockable
    class Construction(object):
        def __init__(self):
            self.material = Material()

        def lock(self):
            self._locked = True
            self.material._locked = True

        def unlock(self):
            self._locked = False
            self.material._locked = False

    constr = Construction()
    constr.lock()
    with pytest.raises(AttributeError):
        constr.material = Material()

    with pytest.raises(AttributeError):
        constr.material.r_value = 5

    constr.unlock()
    constr.material = Material()
    constr.material.r_value = 5
    constr.lock()


def test_with_slots():
    """Test the application of the lockable decorator to a class with __slots__."""
    @lockable
    class Foo(object):
        __slots__ = ('bar', '_locked')

        def __init__(self):
            self.bar = 10

    foo = Foo()
    foo.bar = 20

    foo.lock()
    with pytest.raises(AttributeError):
        foo.bar = 30

    foo.unlock()
    foo.bar = 30
    foo.lock()


def test_with_slots_incorrect():
    """Test the lockable decorator on a class with an incorrect use of __slots__."""
    with pytest.raises(AttributeError):
        @lockable
        class Foo(object):
            __slots__ = ('bar',)

            def __init__(self):
                self.bar = 10


def test_with_slots_inheritance():
    """Test the lockable decorator for a class with __slots__ and inheritance."""
    @lockable
    class Bar(object):
        __slots__ = ('_locked',)

        def __init__(self):
            pass

    @lockable
    class Foo(Bar):
        __slots__ = ('bar',)

        def __init__(self):
            self.bar = 10

    foo = Foo()
    foo.bar = 20

    foo.lock()
    with pytest.raises(AttributeError):
        foo.bar = 30

    foo.unlock()
    foo.bar = 30
    foo.lock()
