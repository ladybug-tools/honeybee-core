# coding=utf-8
"""Utilities to convert any dictionary to Python objects.

Note that importing this module will import almost all modules within the
library in order to be able to re-serialize almost any dictionary produced
from the library.
"""
from honeybee.model import Model
from honeybee.room import Room
from honeybee.face import Face
from honeybee.aperture import Aperture
from honeybee.door import Door
from honeybee.shade import Shade
import honeybee.boundarycondition as hbc


def dict_to_object(honeybee_dict, raise_exception=True):
    """Re-serialize a dictionary of almost any object within honeybee.

    This includes any Model, Room, Face, Aperture, Door, Shade, or boundary
    condition object.

    Args:
        honeybee_dict: A dictionary of any Honeybee object. Note
            that this should be a non-abridged dictionary to be valid.
        raise_exception: Boolean to note whether an excpetion should be raised
            if the object is not identified as a part of honeybee.
            Default: True.

    Returns:
        A Python object derived from the input honeybee_dict.
    """
    try:  # get the type key from the dictionary
        obj_type = honeybee_dict['type']
    except KeyError:
        raise ValueError('Honeybee dictionary lacks required "type" key.')

    if obj_type == 'Model':
        return Model.from_dict(honeybee_dict)
    elif obj_type == 'Room':
        return Room.from_dict(honeybee_dict)
    elif obj_type == 'Face':
        return Face.from_dict(honeybee_dict)
    elif obj_type == 'Aperture':
        return Aperture.from_dict(honeybee_dict)
    elif obj_type == 'Door':
        return Door.from_dict(honeybee_dict)
    elif obj_type == 'Shade':
        return Shade.from_dict(honeybee_dict)
    elif hasattr(hbc, obj_type):
        bc_class = getattr(hbc, obj_type)
        return bc_class.from_dict(honeybee_dict)
    elif raise_exception:
        raise ValueError('{} is not a recognized honeybee object'.format(obj_type))
