# coding: utf-8
"""Extension properties for Model, Room, Face, Shade, Aperture, Door.

These objects hold all attributes assigned by extensions like honeybee-radiance
and honeybee-energy.  Note that these Property objects are not intended to exist
on their own but should have a host object.
"""


class _Properties(object):
    """Base class for all Properties classes."""
    _do_not_duplicate = ('host', 'to_dict', 'ToString')

    def __init__(self, host):
        """Initialize properties.

        Args:
            host: A honeybee-core geometry object that hosts these properties
                (ie. Model, Room, Face, Shade, Aperture, Door).
        """
        self._host = host

    @property
    def host(self):
        """Get the object hosting these properties."""
        return self._host

    def _duplicate_extension_attr(self, original_properties):
        """Duplicate the attributes added by extensions.

        This method should be called within the duplicate or __copy__ methods of
        each honeybee-core geometry object after the core object has been duplicated.
        This method only needs to be called on the new (duplicated) core object and
        the extension properties of the original core object should be passed to
        this method as the original_properties.

        Args:
            original_properties: The properties object of the original core
                object from which the duplicate was derived.
        """
        attr = [atr for atr in dir(self)
                if not atr.startswith('_') and atr not in self._do_not_duplicate]

        for atr in attr:
            var = getattr(original_properties, atr)
            if not hasattr(var, 'duplicate'):
                continue
            try:
                setattr(self, '_' + atr, var.duplicate(self.host))
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise Exception('Failed to duplicate {}: {}'.format(var, e))

    def _add_extension_attr_to_dict(self, base, abridged, include):
        """Add attributes for extensions to the base dictionary.

        This method should be called within the to_dict method of each honeybee-core
        geometry object.

        Args:
            base: The dictionary of the core object without any extension attributes.
                This method will add extension attributes to this dictionary. For
                example, energy properties will appear under base['properties']['energy'].
            abridged: Boolean to note whether the attributes of the extensions should
                be abridged (True) or full (False). For example, if a Room's energy
                properties are abridged, the program_type attribute under the energy
                properties dictionary will just be the name of the program_type. If
                it is full (not abridged), the program_type will be a complete
                dictionary following the ProgramType schema. Abridged dictionaries
                should be used within the Model.to_dict but full dictionaries should
                be used within the to_dict methods of individual objects.
            include: List of properties to filter keys that must be included in
                output dictionary. For example ['energy'] will include 'energy' key if
                available in properties to_dict. By default all the keys will be
                included. To exclude all the keys from extensions use an empty list.
        """
        if include is not None:
            attr = include
        else:
            attr = [atr for atr in dir(self)
                    if not atr.startswith('_') and atr not in self._do_not_duplicate]

        for atr in attr:
            var = getattr(self, atr)
            if not hasattr(var, 'to_dict'):
                continue
            try:
                base.update(var.to_dict(abridged))
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise Exception('Failed to convert {} to a dict: {}'.format(var, e))
        return base

    def _load_extension_attr_from_dict(self, property_dict):
        """Get attributes for extensions from a dictionary of the properties.

        This method should be called within the from_dict method of each honeybee-core
        geometry object. Specifically, this method should be called on the core
        object after it has been created from a dictionary but lacks any of the
        extension attributes in the dictionary.

        Args:
            property_dict: A dictionary of properties for the object (ie.
                FaceProperties, RoomProperties). These will be used to load
                attributes from the dictionary and assign them to the object on
                which this method is called.
        """
        attr = [atr for atr in dir(self)
                if not atr.startswith('_') and atr not in self._do_not_duplicate]

        for atr in attr:
            var = getattr(self, atr)
            if not hasattr(var, 'from_dict'):
                continue
            try:
                setattr(self, '_' + atr, var.__class__.from_dict(
                    property_dict[atr], self.host))
            except KeyError:
                pass  # the property_dict possesses no properties for that extension

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Properties representation."""
        return 'BaseProperties'


class ModelProperties(_Properties):
    """Honeybee Model Properties.

    Model properties. This class will be extended by extensions.

    Usage:
        model = Model('New Elementary School', list_of_rooms)
        model.properties -> ModelProperties
        model.properties.radiance -> ModelRadianceProperties
        model.properties.energy -> ModelEnergyProperties
    """

    def to_dict(self, include=None):
        """Convert properties to dictionary.

        Args:
            include: A list of keys to be included in dictionary.
                If None all the available keys will be included.
        """
        base = {
            'type': 'ModelProperties'
        }
        if include is not None:
            attr = include
        else:
            attr = [atr for atr in dir(self)
                    if not atr.startswith('_') and atr != 'host']

        for atr in attr:
            var = getattr(self, atr)
            if not hasattr(var, 'to_dict'):
                continue
            try:
                base.update(var.to_dict())  # no abridged dictionary for model
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise Exception('Failed to convert {} to a dict: {}'.format(var, e))
        return base

    def apply_properties_from_dict(self, data):
        """Apply extension properties from a Model dictionary to the host Model.

        Args:
            data: A dictionary representation of an entire honeybee-core Model.
        """
        attr = [atr for atr in dir(self)
                if not atr.startswith('_') and atr not in self._do_not_duplicate]

        for atr in attr:
            if atr not in data['properties']:
                continue
            var = getattr(self, atr)
            if not hasattr(var, 'apply_properties_from_dict'):
                continue
            try:
                var.apply_properties_from_dict(data)
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise Exception(
                    'Failed to apply {} properties to the Model: {}'.format(atr, e))

    def __repr__(self):
        """Properties representation."""
        return 'ModelProperties'


class RoomProperties(_Properties):
    """Honeybee Room Properties.

    Room properties. This class will be extended by extensions.

    Usage:
        room = Room('Bedroom', geometry)
        room.properties -> RoomProperties
        room.properties.radiance -> RoomRadianceProperties
        room.properties.energy -> RoomEnergyProperties
    """

    def to_dict(self, abridged=False, include=None):
        """Convert properties to dictionary.

        Args:
            abridged: Boolean to note whether the full dictionary describing the
                object should be returned (False) or just an abridged version (True).
                Default: False.
            include: A list of keys to be included in dictionary.
                If None all the available keys will be included.
        """
        base = {'type': 'RoomProperties'} if not abridged else \
            {'type': 'RoomPropertiesAbridged'}

        base = self._add_extension_attr_to_dict(base, abridged, include)
        return base

    def __repr__(self):
        """Properties representation."""
        return 'RoomProperties'


class FaceProperties(_Properties):
    """Honeybee Face Properties.

    Face properties. This class will be extended by extensions.

    Usage:
        face = Face('South Bedroom Wall', geometry)
        face.properties -> FaceProperties
        face.properties.radiance -> FaceRadianceProperties
        face.properties.energy -> FaceEnergyProperties
    """

    def to_dict(self, abridged=False, include=None):
        """Convert properties to dictionary.

        Args:
            abridged: Boolean to note whether the full dictionary describing the
                object should be returned (False) or just an abridged version (True).
                Default: False.
            include: A list of keys to be included in dictionary besides Face type
                and boundary_condition. If None all the available keys will be included.
        """
        base = {'type': 'FaceProperties'} if not abridged else \
            {'type': 'FacePropertiesAbridged'}
        base = self._add_extension_attr_to_dict(base, abridged, include)
        return base

    def __repr__(self):
        """Properties representation."""
        return 'FaceProperties: {}'.format(self.host.display_name)


class ShadeProperties(_Properties):
    """Honeybee Shade Properties.

    Shade properties. This class will be extended by extensions.

    Usage:
        shade = Shade('Deep Overhang', geometry)
        shade.properties -> ShadeProperties
        shade.properties.radiance -> ShadeRadianceProperties
        shade.properties.energy -> ShadeEnergyProperties
    """

    def to_dict(self, abridged=False, include=None):
        """Convert properties to dictionary.

        Args:
            abridged: Boolean to note whether the full dictionary describing the
                object should be returned (False) or just an abridged version (True).
                Default: False.
            include: A list of keys to be included in dictionary.
                If None all the available keys will be included.
        """
        base = {'type': 'ShadeProperties'} if not abridged else \
            {'type': 'ShadePropertiesAbridged'}

        base = self._add_extension_attr_to_dict(base, abridged, include)
        return base

    def __repr__(self):
        """Properties representation."""
        return 'ShadeProperties: {}'.format(self.host.display_name)


class ApertureProperties(_Properties):
    """Honeybee Aperture Properties.

    Aperture properties. This class will be extended by extensions.

    Usage:
        aperture = Aperture('Window to My Soul', geometry)
        aperture.properties -> ApertureProperties
        aperture.properties.radiance -> ApertureRadianceProperties
        aperture.properties.energy -> ApertureEnergyProperties
    """

    def to_dict(self, abridged=False, include=None):
        """Convert properties to dictionary.

        Args:
            abridged: Boolean to note whether the full dictionary describing the
                object should be returned (False) or just an abridged version (True).
                Default: False.
            include: A list of keys to be included in dictionary.
                If None all the available keys will be included.
        """
        base = {'type': 'ApertureProperties'} if not abridged else \
            {'type': 'AperturePropertiesAbridged'}

        base = self._add_extension_attr_to_dict(base, abridged, include)
        return base

    def __repr__(self):
        """Properties representation."""
        return 'ApertureProperties: {}'.format(self.host.display_name)


class DoorProperties(_Properties):
    """Honeybee Door Properties.

    Door properties. This class will be extended by extensions.

    Usage:
        door = Door('Front Door', geometry)
        door.properties -> DoorProperties
        door.properties.radiance -> DoorRadianceProperties
        door.properties.energy -> DoorEnergyProperties
    """

    def to_dict(self, abridged=False, include=None):
        """Convert properties to dictionary.

        Args:
            abridged: Boolean to note whether the full dictionary describing the
                object should be returned (False) or just an abridged version (True).
                Default: False.
            include: A list of keys to be included in dictionary.
                If None all the available keys will be included.
        """
        base = {'type': 'DoorProperties'} if not abridged else \
            {'type': 'DoorPropertiesAbridged'}

        base = self._add_extension_attr_to_dict(base, abridged, include)
        return base

    def __repr__(self):
        """Properties representation."""
        return 'DoorProperties: {}'.format(self.host.display_name)
