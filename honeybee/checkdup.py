# coding=utf-8
"""Utilities to check whether there are any duplicate values in a list of ids."""

import collections


def check_duplicate_identifiers(objects_to_check, raise_exception=True, obj_name=''):
    """Check whether there are duplicated identifiers across a list of objects.

    Args:
        objects_to_check: A list of honeybee objects across which duplicate
            identifiers will be checked.
        raise_exception: Boolean to note whether an excpetion should be raised if
            duplicated identifiers are found. (Default: True).
        obj_name: An optional name for the object to be included in the error
            message. Fro example, 'Room', 'Face', 'Aperture'.

    Returns:
        A message string indicating the duplicated identifiers that were found.
        This string will be empty if no duplicates were found.
    """
    obj_id_iter = (obj.identifier for obj in objects_to_check)
    dup = [t for t, c in collections.Counter(obj_id_iter).items() if c > 1]
    if len(dup) != 0:
        msg = 'The following duplicated {} identifiers were found:\n{}'.format(
            obj_name, '\n'.join(dup))
        if raise_exception:
            raise ValueError(msg)
        return msg
    return ''


def check_duplicate_identifiers_parent(
        objects_to_check, raise_exception=True, obj_name=''):
    """Check whether there are duplicated identifiers across a list of objects.

    The error message will include the identifiers of top-level parents in order
    to make it easier to find the duplicated objects in the model.

    Args:
        objects_to_check: A list of honeybee objects across which duplicate
            identifiers will be checked. These objects must have the ability to
            have parents for this method to run correctly.
        raise_exception: Boolean to note whether an excpetion should be raised if
            duplicated identifiers are found. (Default: True).
        obj_name: An optional name for the object to be included in the error
            message. Fro example, 'Room', 'Face', 'Aperture'.

    Returns:
        A message string indicating the duplicated identifiers that were found.
        This string will be empty if no duplicates were found.
    """
    obj_id_iter = (obj.identifier for obj in objects_to_check)
    dup = [t for t, c in collections.Counter(obj_id_iter).items() if c > 1]
    if len(dup) != 0:
        top_par = []
        for obj_id in dup:
            rel_parents = []
            for obj in objects_to_check:
                if obj.identifier == obj_id:
                    if obj.has_parent:
                        try:
                            par_obj = obj.top_level_parent
                        except AttributeError:
                            par_obj = obj.parent
                        rel_parents.append(par_obj)
            top_par.append(rel_parents)
        msg = 'The following duplicated {} identifiers were found:\n'.format(obj_name)
        for obj_id, rel_par in zip(dup, top_par):
            obj_msg = obj_id + '\n'
            if len(rel_par) != 0:
                obj_msg += '  Relevant Top-Level Parents:\n'
                for par_o in rel_par:
                    obj_msg += '    {} "{}"\n'.format(
                        par_o.__class__.__name__, par_o.full_id)
            msg += obj_msg
        msg = msg.strip()
        if raise_exception:
            raise ValueError(msg)
        return msg
    return ''
