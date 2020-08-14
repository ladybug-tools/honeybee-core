"""Test the typing functions."""
from honeybee.typing import clean_string, clean_rad_string, clean_ep_string, \
    float_in_range, int_in_range, float_positive, int_positive, \
    tuple_with_length, list_with_length, normpath, \
    clean_and_id_string, clean_and_id_rad_string, clean_and_id_ep_string, \
    float_in_range_excl, float_in_range_excl_incl, float_in_range_incl_excl

import pytest


def test_clean_string():
    """Test the clean_string method."""
    correct_str = '0.5 in. Gypsum Wall'
    incorrect_str = '0.5 in., Gypsum Wall'
    long_str = 'This is an exceptionally long text string that should never be used ' \
        'for the name of anything in EnergyPlus for whatever reason'

    assert clean_string(correct_str) == '0.5in.GypsumWall'
    assert clean_string(incorrect_str) == '0.5in.GypsumWall'
    with pytest.raises(AssertionError):
        clean_string(long_str)


def test_clean_rad_string():
    """Test the clean_rad_string method."""
    correct_str = '0.5 in. Gypsum Wall'
    incorrect_str = '0.5 in., Gypsum Wall'
    long_str = 'This is an exceptionally long text string that should never be used ' \
        'for the name of anything in EnergyPlus but is actually ok for Radiance'

    assert clean_rad_string(correct_str) == '0.5in.GypsumWall'
    assert clean_rad_string(incorrect_str) == '0.5in.GypsumWall'
    clean_rad_string(long_str)


def test_clean_ep_string():
    """Test the clean_ep_string method."""
    correct_str = '1/2 in. Gypsum Board'
    incorrect_str = '1/2 in., Gypsum Board!'
    long_str = 'This is an exceptionally long text string that should never be used ' \
        'for the name of anything in EnergyPlus'

    assert clean_ep_string(correct_str) == correct_str
    assert clean_ep_string(incorrect_str) == correct_str
    with pytest.raises(AssertionError):
        clean_ep_string(long_str)


def test_clean_and_id_string():
    """Test the clean_and_id_string method."""
    correct_str = '0.5 in. Gypsum Wall'
    incorrect_str = '0.5 in., Gypsum Wall'
    long_str = 'This is an exceptionally long text string that should never be used ' \
        'for the name of anything in EnergyPlus for whatever reason'

    assert clean_and_id_string(correct_str).startswith('0.5in.GypsumWall')
    assert clean_and_id_string(incorrect_str).startswith('0.5in.GypsumWall')
    assert len(clean_and_id_string(long_str)) < 70


def test_clean_and_id_rad_string():
    """Test the clean_and_id_rad_string method."""
    correct_str = '0.5 in. Gypsum Wall'
    incorrect_str = '0.5 in., Gypsum Wall'
    long_str = 'This is an exceptionally long text string that should never be used ' \
        'for the name of anything in EnergyPlus but is actually ok for Radiance'

    assert clean_and_id_rad_string(correct_str).startswith('0.5in.GypsumWall')
    assert clean_and_id_rad_string(incorrect_str).startswith('0.5in.GypsumWall')
    assert len(clean_and_id_rad_string(long_str)) > 70


def test_clean_ep_string():
    """Test the clean_and_id_ep_string method."""
    correct_str = '1/2 in. Gypsum Board'
    incorrect_str = '1/2 in., Gypsum Board!'
    long_str = 'This is an exceptionally long text string that should never be used ' \
        'for the name of anything in EnergyPlus'

    assert clean_and_id_ep_string(correct_str).startswith(correct_str)
    assert clean_and_id_ep_string(incorrect_str).startswith(correct_str)
    assert len(clean_and_id_ep_string(long_str)) < 70


def test_float_in_range():
    """Test the float_in_range method."""
    assert isinstance(float_in_range(2.0, 0, 10, 'test number'), float)
    assert isinstance(float_in_range(2, 0, 10, 'test number'), float)
    assert isinstance(float_in_range('2', 0, 10, 'test number'), float)

    with pytest.raises(AssertionError):
        assert isinstance(float_in_range(2, 0, 1, 'test number'), float)
    with pytest.raises(TypeError):
        assert isinstance(float_in_range('two', 0, 10, 'test number'), float)
    with pytest.raises(TypeError):
        assert isinstance(float_in_range([2], 0, 10, 'test number'), float)

    try:
        float_in_range(2, 0, 1, 'test number')
    except AssertionError as e:
        assert 'test number' in str(e)


def test_float_in_range_excl():
    """Test the float_in_range_excl method."""
    assert isinstance(float_in_range_excl(1.0, 0, 10, 'test number'), float)
    assert isinstance(float_in_range_excl('1', 0, 10, 'test number'), float)

    with pytest.raises(AssertionError):
        assert isinstance(float_in_range_excl(0, 0, 10, 'test number'), float)
    with pytest.raises(AssertionError):
        assert isinstance(float_in_range_excl(10, 0, 10, 'test number'), float)

    try:
        float_in_range_excl(2, 0, 1, 'test number')
    except AssertionError as e:
        assert 'test number' in str(e)


def test_float_in_range_excl_incl():
    """Test the float_in_range_excl_incl method."""
    assert isinstance(float_in_range_excl_incl(1, 0, 10, 'test number'), float)
    assert isinstance(float_in_range_excl_incl(10, 0, 10, 'test number'), float)
    assert isinstance(float_in_range_excl_incl('1', 0, 10, 'test number'), float)

    with pytest.raises(AssertionError):
        assert isinstance(float_in_range_excl_incl(0, 0, 10, 'test number'), float)

    try:
        float_in_range_excl_incl(2, 0, 1, 'test number')
    except AssertionError as e:
        assert 'test number' in str(e)


def test_float_in_range_incl_excl():
    """Test the float_in_range_incl_excl method."""
    assert isinstance(float_in_range_incl_excl(1, 0, 10, 'test number'), float)
    assert isinstance(float_in_range_incl_excl(0, 0, 10, 'test number'), float)
    assert isinstance(float_in_range_incl_excl('1', 0, 10, 'test number'), float)

    with pytest.raises(AssertionError):
        assert isinstance(float_in_range_incl_excl(10, 0, 10, 'test number'), float)

    try:
        float_in_range_incl_excl(2, 0, 1, 'test number')
    except AssertionError as e:
        assert 'test number' in str(e)


def test_int_in_range():
    """Test the float_in_range method."""
    assert isinstance(int_in_range(2.0, 0, 10), int)
    assert isinstance(int_in_range(2, 0, 10), int)
    assert isinstance(int_in_range('2', 0, 10), int)

    with pytest.raises(AssertionError):
        assert isinstance(int_in_range(2, 0, 1), float)
    with pytest.raises(TypeError):
        assert isinstance(int_in_range('two', 0, 10), float)
    with pytest.raises(TypeError):
        assert isinstance(int_in_range([2], 0, 10), float)

    try:
        int_in_range(2, 0, 1, 'test number')
    except AssertionError as e:
        assert 'test number' in str(e)


def test_float_positive():
    """Test the float_positive method."""
    assert isinstance(float_positive(2.0), float)
    assert isinstance(float_positive(2), float)
    assert isinstance(float_positive('2'), float)

    with pytest.raises(AssertionError):
        assert isinstance(float_positive(-2), float)
    with pytest.raises(TypeError):
        assert isinstance(float_positive('two'), float)
    with pytest.raises(TypeError):
        assert isinstance(float_positive([2]), float)

    try:
        float_positive(-2, 'test number')
    except AssertionError as e:
        assert 'test number' in str(e)


def test_int_positive():
    """Test the int_positive method."""
    assert isinstance(int_positive(2.0), int)
    assert isinstance(int_positive(2), int)
    assert isinstance(int_positive('2'), int)

    with pytest.raises(AssertionError):
        assert isinstance(int_positive(-2), float)
    with pytest.raises(TypeError):
        assert isinstance(int_positive('two'), float)
    with pytest.raises(TypeError):
        assert isinstance(int_positive([2]), float)

    try:
        int_positive(-2, 'test number')
    except AssertionError as e:
        assert 'test number' in str(e)


def test_tuple_with_length():
    """Test the tuple_with_length method."""
    assert isinstance(tuple_with_length((1, 2, 3), 3, float, 'test tuple'), tuple)
    assert isinstance(tuple_with_length([1, 2, 3], 3, float, 'test tuple'), tuple)
    assert isinstance(tuple_with_length(range(3), 3, float, 'test tuple'), tuple)
    assert isinstance(tuple_with_length((1.0, 2.0, 3.0), 3, float, 'test tuple'), tuple)
    assert isinstance(tuple_with_length(('1', '2', '3'), 3, float, 'test tuple'), tuple)

    with pytest.raises(AssertionError):
        tuple_with_length((1, 2, 3), 4, float, 'test tuple')
    with pytest.raises(TypeError):
        tuple_with_length(('one', 'two', 'three'), 3, float, 'test tuple')

    try:
        tuple_with_length((1, 2, 3), 4, float, 'test tuple')
    except AssertionError as e:
        assert 'test tuple' in str(e)


def test_list_with_length():
    """Test the list_with_length method."""
    assert isinstance(list_with_length((1, 2, 3), 3, float, 'test list'), list)
    assert isinstance(list_with_length([1, 2, 3], 3, float, 'test list'), list)
    assert isinstance(list_with_length(range(3), 3, float, 'test list'), list)
    assert isinstance(list_with_length((1.0, 2.0, 3.0), 3, float, 'test list'), list)
    assert isinstance(list_with_length(('1', '2', '3'), 3, float, 'test list'), list)

    with pytest.raises(AssertionError):
        list_with_length((1, 2, 3), 4, float, 'test list')
    with pytest.raises(TypeError):
        list_with_length(('one', 'two', 'three'), 3, float, 'test list')

    try:
        list_with_length((1, 2, 3), 4, float, 'test list')
    except AssertionError as e:
        assert 'test list' in str(e)
