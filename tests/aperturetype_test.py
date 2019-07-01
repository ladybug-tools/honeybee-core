"""test Face class."""
from honeybee.aperturetype import Window, aperture_types

import pytest


def test_wall():
    """Test the initialization of the Window aperture type."""
    window_type_1 = Window()
    window_type_2 = aperture_types.window

    str(window_type_1)  # test the string representation
    assert window_type_1 == window_type_2
