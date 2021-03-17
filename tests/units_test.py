"""Test the units functions."""
from honeybee.units import parse_distance_string
import pytest


def test_parse_distance_string():
    """Test the parse_distance_string method."""
    assert parse_distance_string('5', 'Meters') == 5
    assert parse_distance_string('5', 'Feet') == 5

    assert parse_distance_string('5m', 'Meters') == 5
    assert parse_distance_string('5m', 'Feet') == pytest.approx(16.4041995, rel=1e-3)
    assert parse_distance_string('5ft', 'Feet') == 5
    assert parse_distance_string('5ft', 'Meters') == pytest.approx(1.524, rel=1e-3)

    assert parse_distance_string('5000mm', 'Meters') == pytest.approx(5, rel=1e-3)
    assert parse_distance_string('500cm', 'Meters') == pytest.approx(5, rel=1e-3)

    assert parse_distance_string('5 ft', 'Meters') == pytest.approx(1.524, rel=1e-3)

    with pytest.raises(ValueError):
        assert parse_distance_string('5 smoots', 'Meters')
