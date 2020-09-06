# coding=utf-8
"""Utilities to check whether there are any duplicate values in a list of ids."""

import collections


def check_duplicate_identifiers(objects_to_check, raise_exception=True, obj_name=''):
    """Re-serialize a dictionary of almost any object within honeybee.

    Args:
        objects_to_check: A list of honeybee objects across which duplicate
            identifiers will be checked.
        raise_exception: Boolean to note whether an excpetion should be raised if
            duplicated identifiers are found. (Default: True).
        obj_name: An optional name for the object to be included in the error
            message. Fro example, 'Room', 'Face', 'Aperture'.

    Returns:
        True if no duplicates were found. False if duplicates were found.
    """
    obj_id_iter = (obj.identifier for obj in objects_to_check)
    dup = [t for t, c in collections.Counter(obj_id_iter).items() if c > 1]
    if len(dup) != 0:
        if raise_exception:
            msg = 'The following duplicated {} identifiers were found:\n{}'.format(
                obj_name, '\n'.join(dup))
            raise ValueError(msg)
        return False
    return True
