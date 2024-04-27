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
        value = value.replace(' ', '_')  # spaces > underscores for readability
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
        value = value.replace(' ', '_')  # spaces > underscores for readability
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
        value = value.replace(' ', '_')  # spaces > underscores for readability
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
        value = value.replace(' ', '_')  # spaces > underscores for readability
        val = re.sub(r'[^.A-Za-z0-9_-]', '', value)
    except TypeError:
        raise TypeError('Input {} must be a text string. Got {}: {}.'.format(
            input_name, type(value), value))
    return val + '_' + str(uuid.uuid4())[:8]


def clean_and_id_ep_string(value, input_name=''):
    """Clean a string and add 8 unique characters to it to make it unique for EnergyPlus.

    This includes stripping out all illegal characters and removing trailing white spaces.
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


def clean_and_number_string(value, existing_dict, input_name=''):
    """Clean a string and add an integer to it if it is found in the existing_dict.

    The resulting string will be valid for both Radiance and EnergyPlus.

    Args:
        value: The text string to be cleaned and possibly given a unique integer.
        existing_dict: A dictionary where the keys are text strings of existing items
            and the values are the number of times that the item has appeared in
            the model already.
    """
    try:
        value = value.replace(' ', '_')  # spaces > underscores for readability
        val = re.sub(r'[^.A-Za-z0-9_-]', '_', value)
    except TypeError:
        raise TypeError('Input {} must be a text string. Got {}: {}.'.format(
            input_name, type(value), value))
    if len(val) > 95:
        val = val[:95]
    if val in existing_dict:
        existing_dict[val] += 1
        return val + '_' + str(existing_dict[val])
    else:
        existing_dict[val] = 1
        return val


def clean_and_number_rad_string(value, existing_dict, input_name=''):
    """Clean a string for Radiance and add an integer if found in the existing_dict.

    This includes stripping out illegal characters and white spaces.

    Args:
        value: The text string to be cleaned and possibly given a unique integer.
        existing_dict: A dictionary where the keys are text strings of existing items
            and the values are the number of times that the item has appeared in
            the model already.
    """
    try:
        value = value.replace(' ', '_')  # spaces > underscores for readability
        val = re.sub(r'[^.A-Za-z0-9_-]', '_', value)
    except TypeError:
        raise TypeError('Input {} must be a text string. Got {}: {}.'.format(
            input_name, type(value), value))
    if val in existing_dict:
        existing_dict[val] += 1
        return val + '_' + str(existing_dict[val])
    else:
        existing_dict[val] = 1
        return val


def clean_and_number_ep_string(value, existing_dict, input_name=''):
    """Clean a string for EnergyPlus and add an integer if found in the existing_dict.

    This includes stripping out all illegal characters and removing trailing white spaces.
    Strings longer than 95 characters will be truncated before adding the integer.

    Args:
        value: The text string to be cleaned and possibly given a unique integer.
        existing_dict: A dictionary where the keys are text strings of existing items
            and the values are the number of times that the item has appeared in
            the model already.
    """
    try:
        val = ''.join(i for i in value if ord(i) < 128)  # strip out non-ascii
        val = re.sub(r'[,;!\n\t]', '', val)  # strip out E+ special characters
    except TypeError:
        raise TypeError('Input {} must be a text string. Got {}: {}.'.format(
            input_name, type(value), value))
    val = val.strip()
    if len(val) > 95:
        val = val[:95]
    if val in existing_dict:
        existing_dict[val] += 1
        return val + ' ' + str(existing_dict[val])
    else:
        existing_dict[val] = 1
        return val


def truncate_and_id_string(value, truncate_len=32, uuid_len=0, input_name=''):
    """Truncate a string to a length with an option to add unique characters at the end.

    Note that all outputs will always be the truncate_len or less and the uuid_len
    just specifies the number of characters to replace at the end with unique ones.

    The result will be valid for EnergyPlus, Radiance, and likely many more engines
    with different types of character restrictions.
    """
    try:
        value = value.replace(' ', '_')  # spaces > underscores for readability
        val = re.sub(r'[^.A-Za-z0-9_-]', '', value)
    except TypeError:
        raise TypeError('Input {} must be a text string. Got {}: {}.'.format(
            input_name, type(value), value))
    final_len = truncate_len - uuid_len
    if len(val) > final_len:
        val = val[:final_len]
    if uuid_len > 0:
        return val + str(uuid.uuid4())[:uuid_len]
    return val


def fixed_string_length(value, target_len=32):
    """Truncate a string or add trailing spaces to hit a target character length.

    This is useful when trying to construct human-readable tables of text.
    """
    if len(value) > target_len:
        return value[:target_len]
    elif len(value) < target_len:
        return value + ' ' * (target_len - len(value))
    else:
        return value


def readable_short_name(value, max_length=24):
    """Convert a string into a shorter but readable version of itself.

    This is useful when dealing with interfaces of file formats that have very
    strict character limits on names or identifiers (like in DOE-2/eQuest).

    When ths input is less than or equal to the max length, the string will be
    left as-is. If not, then the lower-case vowels will be removed from the name,
    making the result abbreviated but still readable/recognizable. If the result
    is still not shorter than the max length, then spaces will be removed. Lastly,
    if all else fails to meet the max length, the middle characters will be,
    removed leaving the beginning and end as they are, which should typically
    help preserve the uniqueness of the name.

    Note that this method does not do any check for illegal characters and presumes
    that the input is already composed of legal characters.
    """
    # perform an initial check to see if it passes
    if len(value) <= max_length:
        return value
    # strip out lowercase vowels and special characters like dashes
    try:
        value = re.sub(r'[aeiouy_\-]', '', value)
    except TypeError:
        raise TypeError('Input must be a text string. Got {}: {}.'.format(
            type(value), value))
    if len(value) <= max_length:
        return value
    # remove spaces from the string to see if it gets short enough
    value = value.replace(' ', '')
    if len(value) <= max_length:
        return value
    # lastly, remove some characters from the middle to get it to fit
    mid_ind = int(max_length * 0.5)
    assert mid_ind > 3, \
        'Max character length of {} is too restrictive.'.format(max_length)
    end_length = max_length - mid_ind - 1
    value = '{}_{}'.format(value[:mid_ind], value[-end_length:])
    return value


def clean_doe2_string(value, max_length=24):
    """Clean and shorten a string for DOE-2 so that it can be a U-name.

    This includes stripping out all illegal characters (including both non-ASCII
    and DOE-2 specific characters), removing trailing spaces, and passing the
    result through the readable_short_name function to hit the target max_length.
    Note that white spaces can be in the result with the assumption that
    the name will be enclosed in double quotes.

    Note that this method does not do any check to ensure the string is unique.
    """
    try:
        val = ''.join(i for i in value if ord(i) < 128)  # strip out non-ascii
        val = re.sub(r'["\(\)\[\]\,\=\n\t]', '', val)  # remove DOE-2 special characters
        val = val.replace('_', ' ')  # put back white spaces
    except TypeError:
        raise TypeError('Input must be a text string. Got {}: {}.'.format(
            type(value), value))
    val = val.strip()
    return readable_short_name(val, max_length)


def invalid_dict_error(invalid_dict, error):
    """Raise a ValueError for an invalid dictionary that failed to serialize.

    This error message will include the identifier (and display_name) if they are
    present within the invalid_dict, making it easier for ens users to find the
    invalid object within large objects like Models.

    Args:
        invalid_dict: A dictionary of an invalid honeybee object that failed
            to serialize.
        error:
    """
    obj_type = invalid_dict['type'].replace('Abridged', '') \
        if 'type' in invalid_dict else 'Honeybee Object'
    obj_id = invalid_dict['identifier'] if 'identifier' in invalid_dict else ''
    full_id = '{}[{}]'.format(invalid_dict['display_name'], obj_id) \
        if 'display_name' in invalid_dict else obj_id
    raise ValueError('{} "{}" is invalid:\n{}'.format(obj_type, full_id, error))


wrapper = '"' if os.name == 'nt' else '\''
"""String wrapper."""


def normpath(value):
    """Normalize path eliminating double slashes, etc and put it in quotes if needed."""
    value = os.path.normpath(value)
    if ' ' in value:
        value = '{0}{1}{0}'.format(wrapper, value)
    return value
