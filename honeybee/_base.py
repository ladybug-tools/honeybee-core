# coding: utf-8
"""Base class for all geometry objects."""
from ladybug_geometry.geometry3d.pointvector import Point3D

from .typing import valid_string


class _Base(object):
    """A base class for all geometry objects.

    Args:
        identifier: Text string for a unique object ID. Must be < 100 characters and
            not contain any spaces or special characters.

    Properties:
        * identifier
        * display_name
        * full_id
        * user_data
    """
    __slots__ = ('_identifier', '_display_name', '_properties', '_user_data')

    def __init__(self, identifier):
        """Initialize base object."""
        self.identifier = identifier
        self._display_name = None
        self._properties = None
        self._user_data = None

    @property
    def identifier(self):
        """Get or set a text string for the unique object identifier.

        This identifier remains constant as the object is mutated, copied, and
        serialized to different formats (eg. dict, idf, rad). As such, this
        property is used to reference the object across a Model.
        """
        return self._identifier

    @identifier.setter
    def identifier(self, value):
        self._identifier = valid_string(value, 'honeybee object identifier')

    @property
    def display_name(self):
        """Get or set a string for the object name without any character restrictions.

        If not set, this will be equal to the identifier.
        """
        if self._display_name is None:
            return self._identifier
        return self._display_name

    @display_name.setter
    def display_name(self, value):
        if value is not None:
            try:
                value = str(value)
            except UnicodeEncodeError:  # Python 2 machine lacking the character set
                pass  # keep it as unicode
        self._display_name = value

    @property
    def full_id(self):
        """Get a string with both the object display_name and identifier.

        This is formatted as display_name[identifier].

        This is useful in error messages to give users an easy means of finding
        invalid objects within models. If there is no display_name assigned,
        only the identifier will be returned.
        """
        if self._display_name is None:
            return self._identifier
        else:
            return '{}[{}]'.format(self._display_name, self._identifier)

    @property
    def properties(self):
        """Get object properties, including Radiance, Energy and other properties."""
        return self._properties

    @property
    def user_data(self):
        """Get or set an optional dictionary for additional meta data for this object.

        This will be None until it has been set. All keys and values of this
        dictionary should be of a standard Python type to ensure correct
        serialization of the object to/from JSON (eg. str, float, int, list, dict)
        """
        return self._user_data

    @user_data.setter
    def user_data(self, value):
        if value is not None:
            assert isinstance(value, dict), 'Expected dictionary for honeybee ' \
                'object user_data. Got {}.'.format(type(value))
        self._user_data = value

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def display_dict(self):
        """Get a list of DisplayFace3D dictionaries for visualizing the object."""
        return []

    def _changed_dict(self, other_object, tolerance):
        """Get a dictionary reporting changes between this object and another.

        Args:
            other_object: Another object of the same type to be compared to this one.
            tolerance: The tolerance to be used in checking whether the geometry
                has been changed.

        Returns:
            A dictionary with a report of differences. This will be None if there
            are no differences detected between this object and the other object.
        """
        # check whether each type of property has changed
        geo_changed = not other_object.is_geo_equivalent(self, tolerance)
        meta_changed = other_object.properties.is_equivalent(self.properties)
        if not geo_changed and all(meta_changed.values()):
            return None
        # establish the base dictionary
        base_dict = {
            'type': 'ChangedObject',
            'element_type': self.__class__.__name__,
            'element_id': self.identifier,
            'element_name': self.display_name,
            'geometry_changed': geo_changed
        }
        # add booleans for whether metadata changed
        for atr, equiv in meta_changed.items():
            base_dict['{}_changed'.format(atr)] = not equiv
        # add a representation of the geometry if it has changed
        base_dict['geometry'] = other_object.display_dict()
        if geo_changed:
            base_dict['existing_geometry'] = self.display_dict()
        return base_dict

    def _base_report_dict(self, dict_type='AddedObject'):
        """Get a dictionary reporting the object as an addition/deletion to/from a Model.
        """
        return {
            'type': dict_type,
            'element_type': self.__class__.__name__,
            'element_id': self.identifier,
            'element_name': self.display_name,
            'geometry': self.display_dict()
        }

    def _validation_message(
            self, message, raise_exception=True, detailed=False,
            code='000000', extension='Core', error_type='Unknown Error'):
        """Handle a validation error message given various options.

        Args:
            message: Text for the error message.
            raise_exception: Boolean to note whether an ValueError should be
                raised with the message. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).
            code: Text for the error code. (Default: 000000).
            extension: Text for the name of the Honeybee extension for which duplicate
                identifiers are being evaluated. (Default: Core).
            error_type: Text for the type of error. This should be directly linked
                to the error code and should simply be a human-readable version of
                the error code. (Default: Unknown Error).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        # first check whether an exception should be raised or the message returned
        if raise_exception:
            raise ValueError(message)
        if not detailed:
            return message
        # if not, then assemble a dictionary with detailed error information
        error_dict = {
            'type': 'ValidationError',
            'code': code,
            'error_type': error_type,
            'extension_type': extension,
            'element_type': self.__class__.__name__,
            'element_id': [self.identifier],
            'element_name': [self.display_name],
            'message': message
        }
        # add parents to the error dictionary if they exist
        if getattr(self, '_parent', None) is not None:
            parents = []
            rel_obj = self
            while getattr(rel_obj, '_parent', None) is not None:
                rel_obj = getattr(rel_obj, '_parent')
                par_dict = {
                    'parent_type': rel_obj.__class__.__name__,
                    'id': rel_obj.identifier,
                    'name': rel_obj.display_name
                }
                parents.append(par_dict)
            error_dict['parents'] = [parents]
        return [error_dict]

    def _top_parent(self):
        """Get the highest parent object that this object is a part of."""
        if getattr(self, '_parent', None) is not None:
            rel_obj = self
            while getattr(rel_obj, '_parent', None) is not None:
                rel_obj = getattr(rel_obj, '_parent')
            return rel_obj

    @staticmethod
    def _validation_message_child(
            message, child_obj, detailed=False, code='000000', extension='Core',
            error_type='Unknown Error'):
        """Process a validation error message of a child object.

        Args:
            message: Text for the error message.
            child_obj: The child object instance for which the error message is for.
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).
            code: Text for the error code. (Default: 000000).
            extension: Text for the name of the Honeybee extension for which duplicate
                identifiers are being evaluated. (Default: Core).
            error_type: Text for the type of error. This should be directly linked
                to the error code and should simply be a human-readable version of
                the error code. (Default: Unknown Error).

        Returns:
            A string with the message or a dictionary if detailed is True.
        """
        # first check whether an exception should be raised or the message returned
        if not detailed:
            return message
        # if not, then assemble a dictionary with detailed error information
        error_dict = {
            'type': 'ValidationError',
            'code': code,
            'error_type': error_type,
            'extension_type': extension,
            'element_type': child_obj.__class__.__name__,
            'element_id': [child_obj.identifier],
            'element_name': [child_obj.display_name],
            'message': message
        }
        # add parents to the error dictionary
        parents = []
        rel_obj = child_obj
        while getattr(rel_obj, '_parent', None) is not None:
            rel_obj = getattr(rel_obj, '_parent')
            par_dict = {
                'parent_type': rel_obj.__class__.__name__,
                'id': rel_obj.identifier,
                'name': rel_obj.display_name
            }
            parents.append(par_dict)
        error_dict['parents'] = [parents]
        return error_dict

    @staticmethod
    def _from_dict_error_message(obj_dict, exception_obj):
        """Give an error message when the object serialization from_dict fails.

        This error message will include the identifier if it exists in the dict.

        Args:
            obj_dict: The objection dictionary that failed serialization.
            exception_obj: The exception object to be included in the message.
        """
        obj_name = obj_dict['type'] if 'type' in obj_dict else 'Honeybee object'
        full_id = ''
        if 'identifier' in obj_dict and obj_dict['identifier'] is not None:
            full_id = '{}[{}]'.format(obj_dict['display_name'], obj_dict['identifier']) \
                if 'display_name' in obj_dict and obj_dict['display_name'] is not None \
                else obj_dict['identifier']
        msg = '{} "{}" is not valid and is not following honeybee-schema:\n{}'.format(
            obj_name, full_id, exception_obj)
        raise ValueError(msg)

    @staticmethod
    def _display_face(face3d, color):
        """Create a DisplayFace3D dictionary from a Face3D and color."""
        return {
            'type': 'DisplayFace3D',
            'geometry': face3d.to_dict(),
            'color': color.to_dict(),
            'display_mode': 'SurfaceWithEdges'
        }

    @staticmethod
    def _calculate_min(geometry_objects):
        """Calculate min Point3D around an array of geometry with min attributes."""
        first_obj = geometry_objects[0]
        min_pt = [first_obj.min.x, first_obj.min.y, first_obj.min.z]
        for obj in geometry_objects[1:]:
            if obj.min.x < min_pt[0]:
                min_pt[0] = obj.min.x
            if obj.min.y < min_pt[1]:
                min_pt[1] = obj.min.y
            if obj.min.z < min_pt[2]:
                min_pt[2] = obj.min.z
        return Point3D(*min_pt)

    @staticmethod
    def _calculate_max(geometry_objects):
        """Calculate max Point3D around an array of geometry with max attributes."""
        first_obj = geometry_objects[0]
        max_pt = [first_obj.max.x, first_obj.max.y, first_obj.max.z]
        for obj in geometry_objects[1:]:
            if obj.max.x > max_pt[0]:
                max_pt[0] = obj.max.x
            if obj.max.y > max_pt[1]:
                max_pt[1] = obj.max.y
            if obj.max.z > max_pt[2]:
                max_pt[2] = obj.max.z
        return Point3D(*max_pt)

    def __copy__(self):
        new_obj = self.__class__(self.identifier)
        new_obj._display_name = self._display_name
        new_obj._user_data = None if self.user_data is None else self.user_data.copy()
        return new_obj

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        return 'Honeybee Base Object: %s' % self.display_name
