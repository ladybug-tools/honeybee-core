"""Collection of methods for type input checking."""
import re
import os
import math
import uuid

try:
    INFPOS = math.inf
    INFNEG = -1 * math.inf
except AttributeError:
    # python 2
    INFPOS = float('inf')
    INFNEG = float('-inf')


def valid_string(value, input_name=''):
    """Check that a string is valid for both Radiance and EnergyPlus.

    This is used for honeybee geometry object names.
    """
    try:
        illegal_match = re.search(r'[^.A-Za-z0-9_-]', value)
    except TypeError:
        raise TypeError('Input {} must be a text string. Got {}: {}.'.format(
            input_name, type(value), value))
    assert illegal_match is None, 'Illegal character "{}" found in {}'.format(
        illegal_match.group(0), input_name)
    assert len(value) > 0, 'Input {} "{}" contains no characters.'.format(
        input_name, value)
    assert len(value) <= 100, 'Input {} "{}" must be less than 100 characters.'.format(
        input_name, value)
    return value


def valid_rad_string(value, input_name=''):
    """Check that a string is valid for Radiance.

    This is used for radiance modifier names, etc.
    """
    try:
        illegal_match = re.search(r'[^.A-Za-z0-9_-]', value)
    except TypeError:
        raise TypeError('Input {} must be a text string. Got {}: {}.'.format(
            input_name, type(value), value))
    assert illegal_match is None, 'Illegal character "{}" found in {}'.format(
        illegal_match.group(0), input_name)
    assert len(value) > 0, 'Input {} "{}" contains no characters.'.format(
        input_name, value)
    return value


def valid_ep_string(value, input_name=''):
    """Check that a string is valid for EnergyPlus.

    This is used for energy material names, schedule names, etc.
    """
    try:
        non_ascii = tuple(i for i in value if ord(i) >= 128)
    except TypeError:
        raise TypeError('Input {} must be a text string. Got {}: {}.'.format(
            input_name, type(value), value))
    assert non_ascii == (), 'Illegal characters {} found in {}'.format(
        non_ascii, input_name)
    illegal_match = re.search(r'[,;!\n\t]', value)
    assert illegal_match is None, 'Illegal character "{}" found in {}'.format(
        illegal_match.group(0), input_name)
    assert len(value) > 0, 'Input {} "{}" contains no characters.'.format(
        input_name, value)
    assert len(value) <= 100, 'Input {} "{}" must be less than 100 characters.'.format(
        input_name, value)
    return value


def _number_check(value, input_name):
    """Check if value is a number."""
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise TypeError('Input {} must be a number. Got {}: {}.'.format(
            input_name, type(value), value))
    return number


def float_in_range(value, mi=INFNEG, ma=INFPOS, input_name=''):
    """Check a float value to be between minimum and maximum."""
    number = _number_check(value, input_name)
    assert mi <= number <= ma, 'Input number {} must be between {} and {}. ' \
        'Got {}'.format(input_name, mi, ma, value)
    return number


def float_in_range_excl(value, mi=INFNEG, ma=INFPOS, input_name=''):
    """Check a float value to be greater than minimum and less than maximum."""
    number = _number_check(value, input_name)
    assert mi < number < ma, 'Input number {} must be greater than {} ' \
        'and less than {}. Got {}'.format(input_name, mi, ma, value)
    return number


def float_in_range_excl_incl(value, mi=INFNEG, ma=INFPOS, input_name=''):
    """Check a float value to be greater than minimum and less than/equal to maximum."""
    number = _number_check(value, input_name)
    assert mi < number <= ma, 'Input number {} must be greater than {} and less than ' \
        'or equal to {}. Got {}'.format(input_name, mi, ma, value)
    return number


def float_in_range_incl_excl(value, mi=INFNEG, ma=INFPOS, input_name=''):
    """Check a float value to be greater than/equal to minimum and less than maximum."""
    number = _number_check(value, input_name)
    assert mi <= number < ma, 'Input number {} must be greater than or equal to {} ' \
        'and less than {}. Got {}'.format(input_name, mi, ma, value)
    return number


def int_in_range(value, mi=INFNEG, ma=INFPOS, input_name=''):
    """Check an integer value to be between minimum and maximum."""
    try:
        number = int(value)
    except ValueError:
        # try to convert to float and then digit if possible
        try:
            number = int(float(value))
        except (ValueError, TypeError):
            raise TypeError('Input {} must be an integer. Got {}: {}.'.format(
                input_name, type(value), value))
    except (ValueError, TypeError):
        raise TypeError('Input {} must be an integer. Got {}: {}.'.format(
            input_name, type(value), value))
    assert mi <= number <= ma, 'Input integer {} must be between {} and {}. ' \
        'Got {}.'.format(input_name, mi, ma, value)
    return number


def float_positive(value, input_name=''):
    """Check a float value to be positive."""
    return float_in_range(value, 0, INFPOS, input_name)


def int_positive(value, input_name=''):
    """Check if an integer value is positive."""
    return int_in_range(value, 0, INFPOS, input_name)


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


def clean_string(value, input_name=''):
    """Clean a string so that it is valid for both Radiance and EnergyPlus.

    This will strip out spaces and special characters and raise an error if the
    string is empty after stripping or has more than 100 characters.
    """
    try:
        val = re.sub(r'[^.A-Za-z0-9_-]', '', value)
    except TypeError:
        raise TypeError('Input {} must be a text string. Got {}: {}.'.format(
            input_name, type(value), value))
    assert len(val) > 0, 'Input {} "{}" contains no valid characters.'.format(
        input_name, value)
    assert len(val) <= 100, 'Input {} "{}" must be less than 100 characters.'.format(
        input_name, value)
    return val


def clean_rad_string(value, input_name=''):
    """Clean a string for Radiance that can be used for rad material names.

    This includes stripping out illegal characters and white spaces as well as
    raising an error if no legal characters are found.
    """
    try:
        val = re.sub(r'[^.A-Za-z0-9_-]', '', value)
    except TypeError:
        raise TypeError('Input {} must be a text string. Got {}: {}.'.format(
            input_name, type(value), value))
    assert len(val) > 0, 'Input {} "{}" contains no valid characters.'.format(
        input_name, value)
    return val


def clean_ep_string(value, input_name=''):
    """Clean a string for EnergyPlus that can be used for energy material names.

    This includes stripping out all illegal characters, removing trailing spaces,
    and rasing an error if the name is not longer than 100 characters or no legal
    characters found.
    """
    try:
        val = ''.join(i for i in value if ord(i) < 128)  # strip out non-ascii
        val = re.sub(r'[,;!\n\t]', '', val)  # strip out E+ special characters
    except TypeError:
        raise TypeError('Input {} must be a text string. Got {}: {}.'.format(
            input_name, type(value), value))
    val = val.strip()
    assert len(val) > 0, 'Input {} "{}" contains no valid characters.'.format(
        input_name, value)
    assert len(val) <= 100, 'Input {} "{}" must be less than 100 characters.'.format(
        input_name, value)
    return val


def clean_and_id_string(value, input_name=''):
    """Clean a string and add 8 unique characters to it to make it unique.

    Strings longer than 50 characters will be truncated before adding the ID.
    The resulting string will be valid for both Radiance and EnergyPlus.
    """
    try:
        val = re.sub(r'[^.A-Za-z0-9_-]', '', value)
    except TypeError:
        raise TypeError('Input {} must be a text string. Got {}: {}.'.format(
            input_name, type(value), value))
    if len(val) > 50:
        val = val[:50]
    return val + '_' + str(uuid.uuid4())[:8]


def clean_and_id_rad_string(value, input_name=''):
    """Clean a string and add 8 unique characters to it to make it unique for Radiance.

    This includes stripping out illegal characters and white spaces.
    """
    try:
        val = re.sub(r'[^.A-Za-z0-9_-]', '', value)
    except TypeError:
        raise TypeError('Input {} must be a text string. Got {}: {}.'.format(
            input_name, type(value), value))
    return val + '_' + str(uuid.uuid4())[:8]


def clean_and_id_ep_string(value, input_name=''):
    """Clean a string and add 8 unique characters to it to make it unique for EnergyPlus.

    This includes stripping out all illegal charactersand removing trailing white spaces.
    Strings longer than 50 characters will be truncated before adding the ID.
    """
    try:
        val = ''.join(i for i in value if ord(i) < 128)  # strip out non-ascii
        val = re.sub(r'[,;!\n\t]', '', val)  # strip out E+ special characters
    except TypeError:
        raise TypeError('Input {} must be a text string. Got {}: {}.'.format(
            input_name, type(value), value))
    val = val.strip()
    if len(val) > 50:
        val = val[:50]
    return val + '_' + str(uuid.uuid4())[:8]


wrapper = '"' if os.name == 'nt' else '\''
"""String wrapper."""


def normpath(value):
    """Normalize path eliminating double slashes, etc and put it in quotes if needed."""
    value = os.path.normpath(value)
    if ' ' in value:
        value = '{0}{1}{0}'.format(wrapper, value)
    return value
