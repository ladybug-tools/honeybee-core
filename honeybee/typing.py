"""Collection of methods for type input checking."""
import re


def valid_string(value, input_name=''):
    """Get a valid string for both Radaince and EnergyPlus.

    This is used for honeybee face and honeybee zone names.
    """
    try:
        val = re.sub(r'[^.A-Za-z0-9_-]', '', value)
    except TypeError:
        raise TypeError('Input {} must be a text string. Got {}.'.format(
            input_name, type(value)))
    assert len(val) > 0, 'Input {} "{}" contains no valid characters.'.format(
        input_name, value)
    assert len(val) <= 100, 'Input {} "{}" must be less than 100 characters.'.format(
        input_name, value)
    return val


def valid_rad_string(value, input_name=''):
    """Get a valid string for Radaince that can be used for rad material names, etc.

    This includes stripping out illegal characters and white spaces.
    """
    try:
        val = re.sub(r'[^.A-Za-z0-9_-]', '', value)
    except TypeError:
        raise TypeError('Input {} must be a text string. Got {}.'.format(
            input_name, type(value)))
    assert len(val) > 0, 'Input {} "{}" contains no valid characters.'.format(
        input_name, value)
    return val


def valid_ep_string(value, input_name=''):
    """Get valid string for EnergyPlus that can be used for energy material names, etc.

    This includes stripping out all illegal characters, removing trailing white spaces,
    and ensuring the name is not longer than 100 characters.
    """
    try:
        val = re.sub(r'[^.\sA-Za-z0-9_-]', '', value)
    except TypeError:
        raise TypeError('Input {} must be a text string. Got {}.'.format(
            input_name, type(value)))
    val = val.strip()
    assert len(val) > 0, 'Input {} "{}" contains no valid characters.'.format(
        input_name, value)
    assert len(val) <= 100, 'Input {} "{}" must be less than 100 characters.'.format(
        input_name, value)
    return val


def float_in_range(value, mi=0.0, ma=1.0, input_name=''):
    """Check a float value to be between minimum and maximum."""
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise TypeError('Input {} must be a number. Got {}.'.format(
            input_name, type(value)))
    assert mi <= number <= ma, 'Input number {} must be between {} and {}. ' \
        'Got {}'.format(input_name, mi, ma, value)
    return number


def int_in_range(value, mi=0.0, ma=1.0, input_name=''):
    """Check an integer value to be between minimum and maximum."""
    try:
        number = int(value)
    except (ValueError, TypeError):
        raise TypeError('Input {} must be an integer. Got {}.'.format(
            input_name, type(value)))
    assert mi <= number <= ma, 'Input integer {} must be between {} and {}. ' \
        'Got {}.'.format(input_name, mi, ma, value)
    return number


def float_positive(value, input_name=''):
    """Check a float value to be positive."""
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise TypeError('Input {} must be a number. Got {}.'.format(
            input_name, type(value)))
    assert 0 <= number, 'Input {} "{}" must be positive.'.format(input_name, number)
    return number


def int_positive(value, input_name=''):
    """Check if an integer value is positive."""
    try:
        number = int(value)
    except (ValueError, TypeError):
        raise TypeError('Input {} must be an integer. Got {}.'.format(
            input_name, type(value)))
    assert 0 <= number, 'Input {} ({}) must be positive.'.format(input_name, number)
    return number


def tuple_with_length(value, length=3, item_type=float, input_name=''):
    """Try to create a tuple with a certain value."""
    try:
        value = tuple(item_type(v) for v in value)
    except (ValueError, TypeError):
        raise TypeError('Input {} must be a {}.'.format(
            input_name, item_type))
    assert len(value) == length, 'Input {} length must be {} not {}'.format(
        input_name, length, len(value))
    return value


def list_with_length(value, length=3, item_type=float, input_name=''):
    """Try to create a list with a certain value."""
    try:
        value = [item_type(v) for v in value]
    except (ValueError, TypeError):
        raise TypeError('Input {} must be a {}.'.format(
            input_name, item_type))
    assert len(value) == length, 'Input {} length must be {} not {}'.format(
        input_name, length, len(value))
    return value
