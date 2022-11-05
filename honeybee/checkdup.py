# coding=utf-8
"""Utilities to check whether there are any duplicate values in a list of ids."""

import collections


def check_duplicate_identifiers(
        objects_to_check, raise_exception=True, obj_name='', detailed=False,
        code='000000', extension='Core', error_type='Duplicate Object Identifier'):
    """Check whether there are duplicated identifiers across a list of objects.

    Args:
        objects_to_check: A list of honeybee objects across which duplicate
            identifiers will be checked.
        raise_exception: Boolean to note whether an exception should be raised if
            duplicated identifiers are found. (Default: True).
        obj_name: An optional name for the object to be included in the error
            message. Fro example, 'Room', 'Face', 'Aperture'.
        detailed: Boolean for whether the returned object is a detailed list of
            dicts with error info or a string with a message. (Default: False).
        code: Text for the error code. (Default: 0000).
        extension: Text for the name of the Honeybee extension for which duplicate
            identifiers are being evaluated. (Default: Core).
        error_type: Text for the type of error. This should be directly linked
            to the error code and should simply be a human-readable version of
            the error code. (Default: Unknown Error).

    Returns:
        A message string indicating the duplicated identifiers (if detailed is False)
        or a list of dictionaries with information about the duplicated identifiers
        (if detailed is True). This string (or list) will be empty if no duplicates
        were found.
    """
    detailed = False if raise_exception else detailed
    obj_id_iter = (obj.identifier for obj in objects_to_check)
    dup = [t for t, c in collections.Counter(obj_id_iter).items() if c > 1]
    if len(dup) != 0:
        if detailed:
            err_list = []
            for dup_id in dup:
                msg = 'There is a duplicated {} identifier: {}'.format(obj_name, dup_id)
                dup_dict = {
                    'type': 'ValidationError',
                    'code': code,
                    'error_type': error_type,
                    'extension_type': extension,
                    'element_type': obj_name,
                    'element_id': dup_id,
                    'element_name': dup_id,
                    'message': msg
                }
                err_list.append(dup_dict)
            return err_list
        msg = 'The following duplicated {} identifiers were found:\n{}'.format(
            obj_name, '\n'.join(dup))
        if raise_exception:
            raise ValueError(msg)
        return msg
    return [] if detailed else ''


def check_duplicate_identifiers_parent(
        objects_to_check, raise_exception=True, obj_name='', detailed=False,
        code='000000', extension='Core', error_type='Duplicate Object Identifier'):
    """Check whether there are duplicated identifiers across a list of objects.

    The error message will include the identifiers of top-level parents in order
    to make it easier to find the duplicated objects in the model.

    Args:
        objects_to_check: A list of honeybee objects across which duplicate
            identifiers will be checked. These objects must have the ability to
            have parents for this method to run correctly.
        raise_exception: Boolean to note whether an exception should be raised if
            duplicated identifiers are found. (Default: True).
        obj_name: An optional name for the object to be included in the error
            message. For example, 'Room', 'Face', 'Aperture'.
        detailed: Boolean for whether the returned object is a detailed list of
            dicts with error info or a string with a message. (Default: False).
        code: Text for the error code. (Default: 0000).
        extension: Text for the name of the Honeybee extension for which duplicate
            identifiers are being evaluated. (Default: Core).
        error_type: Text for the type of error. This should be directly linked
            to the error code and should simply be a human-readable version of
            the error code. (Default: Unknown Error).

    Returns:
        A message string indicating the duplicated identifiers (if detailed is False)
        or a list of dictionaries with information about the duplicated identifiers
        (if detailed is True). This string (or list) will be empty if no duplicates
        were found.
    """
    detailed = False if raise_exception else detailed
    obj_id_iter = (obj.identifier for obj in objects_to_check)
    dup = [t for t, c in collections.Counter(obj_id_iter).items() if c > 1]
    if len(dup) != 0:
        # find the relevant top-level parents
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
        # if a detailed dictionary is requested, then create it
        if detailed:
            err_list = []
            for dup_id, rel_par in zip(dup, top_par):
                dup_dict = {
                    'type': 'ValidationError',
                    'code': code,
                    'error_type': error_type,
                    'extension_type': extension,
                    'element_type': obj_name,
                    'element_id': dup_id,
                    'element_name': dup_id
                }
                msg = 'There is a duplicated {} identifier: {}'.format(obj_name, dup_id)
                if len(rel_par) != 0:
                    dup_dict['top_parents'] = []
                    msg += '\n  Relevant Top-Level Parents:\n'
                    for par_o in rel_par:
                        par_dict = {
                            'parent_type': par_o.__class__.__name__,
                            'id': par_o.identifier,
                            'name': par_o.display_name
                        }
                        dup_dict['top_parents'].append(par_dict)
                        msg += '    {} "{}"\n'.format(
                            par_o.__class__.__name__, par_o.full_id)
                dup_dict['message'] = msg
                err_list.append(dup_dict)
            return err_list
        # if just an error message is requested, then build it from the information
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
    return [] if detailed else ''


def is_equivalent(object_1, object_2):
    """Check if two objects are equal with an initial check for the same instance.
    """
    if object_1 is object_2:  # first see if they're the same instance
        return True
    return object_1 == object_2  # two objects that should have == operators
