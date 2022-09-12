# coding: utf-8
"""Honeybee Model."""
from __future__ import division
import os
import sys
import re
import json
import math
import uuid
try:  # check if we are in IronPython
    import cPickle as pickle
except ImportError:  # wea re in cPython
    import pickle

from ladybug_geometry.geometry3d.plane import Plane
from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.interop.stl import STL

from ._base import _Base
from .units import conversion_factor_to_meters, UNITS, UNITS_TOLERANCES
from .checkdup import check_duplicate_identifiers, check_duplicate_identifiers_parent
from .properties import ModelProperties
from .room import Room
from .face import Face
from .shade import Shade
from .aperture import Aperture
from .door import Door
from .typing import float_positive, invalid_dict_error, clean_string
from .config import folders
from .boundarycondition import Surface
from .facetype import AirBoundary
import honeybee.writer.model as writer


class Model(_Base):
    """A collection of Rooms, Faces, Shades, Apertures, and Doors representing a model.

    Args:
        identifier: Text string for a unique Model ID. Must be < 100 characters and
            not contain any spaces or special characters.
        rooms: A list of Room objects in the model.
        orphaned_faces: A list of the Face objects in the model that lack
            a parent Room. Note that orphaned Faces are not acceptable for
            Models that are to be exported for energy simulation.
        orphaned_shades: A list of the Shade objects in the model that lack
            a parent.
        orphaned_apertures: A list of the Aperture objects in the model that lack
            a parent Face. Note that orphaned Apertures are not acceptable for
            Models that are to be exported for energy simulation.
        orphaned_doors: A list of the Door objects in the model that lack
            a parent Face. Note that orphaned Doors are not acceptable for
            Models that are to be exported for energy simulation.
        units: Text for the units system in which the model geometry
            exists. Default: 'Meters'. Choose from the following:

            * Meters
            * Millimeters
            * Feet
            * Inches
            * Centimeters

        tolerance: The maximum difference between x, y, and z values at which
            vertices are considered equivalent. Zero indicates that no tolerance
            checks should be performed. None indicates that the tolerance will be
            set based on the units above, with the tolerance consistently being
            between 1 cm and 1 mm (roughly the tolerance implicit in the OpenStudio
            SDK and EnergyPlus). (Default: None).
        angle_tolerance: The max angle difference in degrees that vertices are allowed
            to differ from one another in order to consider them colinear. Zero indicates
            that no angle tolerance checks should be performed. (Default: 1.0).

    Properties:
        * identifier
        * display_name
        * units
        * tolerance
        * angle_tolerance
        * rooms
        * faces
        * apertures
        * doors
        * shades
        * indoor_shades
        * outdoor_shades
        * orphaned_faces
        * orphaned_shades
        * orphaned_apertures
        * orphaned_doors
        * stories
        * volume
        * floor_area
        * exposed_area
        * exterior_wall_area
        * exterior_roof_area
        * exterior_aperture_area
        * exterior_wall_aperture_area
        * exterior_skylight_aperture_area
        * user_data
    """
    __slots__ = ('_rooms', '_orphaned_faces', '_orphaned_shades', '_orphaned_apertures',
                 '_orphaned_doors', '_units', '_tolerance', '_angle_tolerance')

    UNITS = UNITS
    UNITS_TOLERANCES = UNITS_TOLERANCES

    def __init__(self, identifier, rooms=None, orphaned_faces=None, orphaned_shades=None,
                 orphaned_apertures=None, orphaned_doors=None,
                 units='Meters', tolerance=None, angle_tolerance=1.0):
        """A collection of Rooms, Faces, Apertures, and Doors for an entire model."""
        _Base.__init__(self, identifier)  # process the identifier

        self.units = units
        self.tolerance = tolerance
        self.angle_tolerance = angle_tolerance

        self._rooms = []
        self._orphaned_faces = []
        self._orphaned_shades = []
        self._orphaned_apertures = []
        self._orphaned_doors = []
        if rooms is not None:
            for room in rooms:
                self.add_room(room)
        if orphaned_faces is not None:
            for face in orphaned_faces:
                self.add_face(face)
        if orphaned_shades is not None:
            for shade in orphaned_shades:
                self.add_shade(shade)
        if orphaned_apertures is not None:
            for aperture in orphaned_apertures:
                self.add_aperture(aperture)
        if orphaned_doors is not None:
            for door in orphaned_doors:
                self.add_door(door)

        self._properties = ModelProperties(self)

    @classmethod
    def from_dict(cls, data):
        """Initialize a Model from a dictionary.

        Args:
            data: A dictionary representation of a Model object.
        """
        # check the type of dictionary
        assert data['type'] == 'Model', 'Expected Model dictionary. ' \
            'Got {}.'.format(data['type'])

        # import the units and tolerance values
        units = 'Meters' if 'units' not in data or data['units'] is None \
            else data['units']
        tol = cls.UNITS_TOLERANCES[units] if 'tolerance' not in data or \
            data['tolerance'] is None else data['tolerance']
        angle_tol = 1.0 if 'angle_tolerance' not in data or \
            data['angle_tolerance'] is None else data['angle_tolerance']

        # import all of the geometry
        rooms = None  # import rooms
        if 'rooms' in data and data['rooms'] is not None:
            rooms = []
            for r in data['rooms']:
                try:
                    rooms.append(Room.from_dict(r, tol, angle_tol))
                except Exception as e:
                    invalid_dict_error(r, e)
        orphaned_faces = None  # import orphaned faces
        if 'orphaned_faces' in data and data['orphaned_faces'] is not None:
            orphaned_faces = []
            for f in data['orphaned_faces']:
                try:
                    orphaned_faces.append(Face.from_dict(f))
                except Exception as e:
                    invalid_dict_error(f, e)
        orphaned_shades = None  # import orphaned shades
        if 'orphaned_shades' in data and data['orphaned_shades'] is not None:
            orphaned_shades = []
            for s in data['orphaned_shades']:
                try:
                    orphaned_shades.append(Shade.from_dict(s))
                except Exception as e:
                    invalid_dict_error(s, e)
        orphaned_apertures = None  # import orphaned apertures
        if 'orphaned_apertures' in data and data['orphaned_apertures'] is not None:
            orphaned_apertures = []
            for a in data['orphaned_apertures']:
                try:
                    orphaned_apertures.append(Aperture.from_dict(a))
                except Exception as e:
                    invalid_dict_error(a, e)
        orphaned_doors = None  # import orphaned doors
        if 'orphaned_doors' in data and data['orphaned_doors'] is not None:
            orphaned_doors = []
            for d in data['orphaned_doors']:
                try:
                    orphaned_doors.append(Door.from_dict(d))
                except Exception as e:
                    invalid_dict_error(d, e)

        # build the model object
        model = Model(data['identifier'], rooms, orphaned_faces, orphaned_shades,
                      orphaned_apertures, orphaned_doors, units, tol, angle_tol)
        if 'display_name' in data and data['display_name'] is not None:
            model.display_name = data['display_name']
        if 'user_data' in data and data['user_data'] is not None:
            model.user_data = data['user_data']

        # assign extension properties to the model
        model.properties.apply_properties_from_dict(data)
        return model

    @classmethod
    def from_file(cls, hb_file):
        """Initialize a Model from a HBJSON or HBpkl file, auto-sensing the type.

        Args:
            hb_file: Path to either a HBJSON or HBpkl file.
        """
        # sense the file type from the first character to avoid maxing memory with JSON
        # this is needed since queenbee overwrites all file extensions
        with open(hb_file) as inf:
            first_char = inf.read(1)
        is_json = True if first_char == '{' else False
        # load the file using either HBJSON pathway or HBpkl
        if is_json:
            return cls.from_hbjson(hb_file)
        return cls.from_hbpkl(hb_file)

    @classmethod
    def from_hbjson(cls, hbjson_file):
        """Initialize a Model from a HBJSON file.

        Args:
            hbjson_file: Path to HBJSON file.
        """
        assert os.path.isfile(hbjson_file), 'Failed to find %s' % hbjson_file
        if (sys.version_info < (3, 0)):
            with open(hbjson_file) as inf:
                data = json.load(inf)
        else:
            with open(hbjson_file, encoding='utf-8') as inf:
                data = json.load(inf)
        return cls.from_dict(data)

    @classmethod
    def from_hbpkl(cls, hbpkl_file):
        """Initialize a Model from a HBpkl file.

        Args:
            hbpkl_file: Path to HBpkl file.
        """
        assert os.path.isfile(hbpkl_file), 'Failed to find %s' % hbpkl_file
        with open(hbpkl_file, 'rb') as inf:
            data = pickle.load(inf)
        return cls.from_dict(data)

    @classmethod
    def from_stl(cls, file_path, geometry_to_faces=False, units='Meters',
                 tolerance=None, angle_tolerance=1.0):
        """Create a Honeybee Model from an STL file.

        Args:
            file_path: Path to an STL file as a text string. The STL file can be
                in either ASCII or binary format.
            geometry_to_faces: A boolean to note whether the geometry in the STL
                file should be imported as Faces (with Walls/Floors/RoofCeiling
                set according to the normal). If False, all geometry will be
                imported as Shades instead of Faces. (Default: False).
            units: Text for the units system in which the model geometry
                exists. Default: 'Meters'. Choose from the following:

                * Meters
                * Millimeters
                * Feet
                * Inches
                * Centimeters

            tolerance: The maximum difference between x, y, and z values at which
                vertices are considered equivalent. Zero indicates that no tolerance
                checks should be performed. None indicates that the tolerance will be
                set based on the units above, with the tolerance consistently being
                between 1 cm and 1 mm (roughly the tolerance implicit in the OpenStudio
                SDK and EnergyPlus). (Default: None).
            angle_tolerance: The max angle difference in degrees that vertices
                are allowed to differ from one another in order to consider them
                colinear. Zero indicates that no angle tolerance checks should be
                performed. (Default: 1.0).
        """
        stl_obj = STL.from_file(file_path)
        all_id = clean_string(stl_obj.name)
        all_geo = []
        for verts, normal in zip(stl_obj.face_vertices, stl_obj.face_normals):
            all_geo.append(Face3D(verts, plane=Plane(normal, verts[0])))
        if geometry_to_faces:
            hb_objs = [Face(all_id + '_' + str(uuid.uuid4())[:8], go) for go in all_geo]
            return Model(all_id, orphaned_faces=hb_objs, units=units,
                         tolerance=tolerance, angle_tolerance=angle_tolerance)
        else:
            hb_objs = [Shade(all_id + '_' + str(uuid.uuid4())[:8], go) for go in all_geo]
            return Model(all_id, orphaned_shades=hb_objs, units=units,
                         tolerance=tolerance, angle_tolerance=angle_tolerance)

    @classmethod
    def from_objects(cls, identifier, objects, units='Meters',
                     tolerance=None, angle_tolerance=1.0):
        """Initialize a Model from a list of any type of honeybee-core geometry objects.

        Args:
            identifier: Text string for a unique Model ID. Must be < 100 characters and
                not contain any spaces or special characters.
            objects: A list of honeybee Rooms, Faces, Shades, Apertures and Doors.
            units: Text for the units system in which the model geometry
                exists. Default: 'Meters'. Choose from the following:

                * Meters
                * Millimeters
                * Feet
                * Inches
                * Centimeters

            tolerance: The maximum difference between x, y, and z values at which
                vertices are considered equivalent. Zero indicates that no tolerance
                checks should be performed. None indicates that the tolerance will be
                set based on the units above, with the tolerance consistently being
                between 1 cm and 1 mm (roughly the tolerance implicit in the OpenStudio
                SDK and EnergyPlus). (Default: None).
            angle_tolerance: The max angle difference in degrees that vertices
                are allowed to differ from one another in order to consider them
                colinear. Zero indicates that no angle tolerance checks should be
                performed. (Default: 1.0).
        """
        rooms = []
        faces = []
        shades = []
        apertures = []
        doors = []
        for obj in objects:
            if isinstance(obj, Room):
                rooms.append(obj)
            elif isinstance(obj, Face):
                faces.append(obj)
            elif isinstance(obj, Shade):
                shades.append(obj)
            elif isinstance(obj, Aperture):
                apertures.append(obj)
            elif isinstance(obj, Door):
                doors.append(obj)
            else:
                raise TypeError('Expected Room, Face, Shade, Aperture or Door '
                                'for Model. Got {}'.format(type(obj)))

        return cls(identifier, rooms, faces, shades, apertures, doors, units,
                   tolerance, angle_tolerance)

    @property
    def units(self):
        """Get or set Text for the units system in which the model geometry exists."""
        return self._units

    @units.setter
    def units(self, value):
        value = value.title()
        assert value in UNITS, '{} is not supported as a units system. ' \
            'Choose from the following: {}'.format(value, self.units)
        self._units = value

    @property
    def tolerance(self):
        """Get or set a number for the max meaningful difference between x, y, z values.

        This value should be in the Model's units. Zero indicates cases
        where no tolerance checks should be performed.
        """
        return self._tolerance

    @tolerance.setter
    def tolerance(self, value):
        self._tolerance = float_positive(value, 'model tolerance') if value is not None \
            else UNITS_TOLERANCES[self.units]

    @property
    def angle_tolerance(self):
        """Get or set a number for the max meaningful angle difference in degrees.

        Face3D normal vectors differing by this amount are not considered parallel
        and Face3D segments that differ from 180 by this amount are not considered
        colinear. Zero indicates cases where no angle_tolerance checks should be
        performed.
        """
        return self._angle_tolerance

    @angle_tolerance.setter
    def angle_tolerance(self, value):
        self._angle_tolerance = float_positive(value, 'model angle_tolerance')

    @property
    def rooms(self):
        """Get a list of all Room objects in the model."""
        return tuple(self._rooms)

    @property
    def faces(self):
        """Get a list of all Face objects in the model."""
        child_faces = [face for room in self._rooms for face in room._faces]
        return child_faces + self._orphaned_faces

    @property
    def apertures(self):
        """Get a list of all Aperture objects in the model."""
        child_apertures = []
        for room in self._rooms:
            for face in room._faces:
                child_apertures.extend(face._apertures)
        for face in self._orphaned_faces:
            child_apertures.extend(face._apertures)
        return child_apertures + self._orphaned_apertures

    @property
    def doors(self):
        """Get a list of all Door objects in the model."""
        child_doors = []
        for room in self._rooms:
            for face in room._faces:
                child_doors.extend(face._doors)
        for face in self._orphaned_faces:
            child_doors.extend(face._doors)
        return child_doors + self._orphaned_doors

    @property
    def shades(self):
        """Get a list of all Shade objects in the model."""
        child_shades = []
        for room in self._rooms:
            child_shades.extend(room.shades)
            for face in room.faces:
                child_shades.extend(face.shades)
                for ap in face._apertures:
                    child_shades.extend(ap.shades)
                for dr in face._doors:
                    child_shades.extend(dr.shades)
        for face in self._orphaned_faces:
            child_shades.extend(face.shades)
            for ap in face._apertures:
                child_shades.extend(ap.shades)
            for dr in face._doors:
                child_shades.extend(dr.shades)
        for ap in self._orphaned_apertures:
            child_shades.extend(ap.shades)
        for dr in self._orphaned_doors:
            child_shades.extend(dr.shades)
        return child_shades + self._orphaned_shades

    @property
    def indoor_shades(self):
        """Get a list of all indoor Shade objects in the model."""
        child_shades = []
        for room in self._rooms:
            child_shades.extend(room._indoor_shades)
            for face in room.faces:
                child_shades.extend(face._indoor_shades)
                for ap in face._apertures:
                    child_shades.extend(ap._indoor_shades)
                for dr in face._doors:
                    child_shades.extend(dr._indoor_shades)
        for face in self._orphaned_faces:
            child_shades.extend(face._indoor_shades)
            for ap in face._apertures:
                child_shades.extend(ap._indoor_shades)
            for dr in face._doors:
                child_shades.extend(dr._indoor_shades)
        for ap in self._orphaned_apertures:
            child_shades.extend(ap._indoor_shades)
        for dr in self._orphaned_doors:
            child_shades.extend(dr._indoor_shades)
        return child_shades

    @property
    def outdoor_shades(self):
        """Get a list of all outdoor Shade objects in the model.

        This includes all of the orphaned_shades.
        """
        child_shades = []
        for room in self._rooms:
            child_shades.extend(room._outdoor_shades)
            for face in room.faces:
                child_shades.extend(face._outdoor_shades)
                for ap in face._apertures:
                    child_shades.extend(ap._outdoor_shades)
                for dr in face._doors:
                    child_shades.extend(dr._outdoor_shades)
        for face in self._orphaned_faces:
            child_shades.extend(face._outdoor_shades)
            for ap in face._apertures:
                child_shades.extend(ap._outdoor_shades)
            for dr in face._doors:
                child_shades.extend(dr._outdoor_shades)
        for ap in self._orphaned_apertures:
            child_shades.extend(ap._outdoor_shades)
        for dr in self._orphaned_doors:
            child_shades.extend(dr._outdoor_shades)
        return child_shades + self._orphaned_shades

    @property
    def orphaned_faces(self):
        """Get a list of all Face objects without parent Rooms in the model."""
        return tuple(self._orphaned_faces)

    @property
    def orphaned_apertures(self):
        """Get a list of all Aperture objects without parent Faces in the model."""
        return tuple(self._orphaned_apertures)

    @property
    def orphaned_doors(self):
        """Get a list of all Door objects without parent Faces in the model."""
        return tuple(self._orphaned_doors)

    @property
    def orphaned_shades(self):
        """Get a list of all Shade objects without parent Rooms in the model."""
        return tuple(self._orphaned_shades)

    @property
    def stories(self):
        """Get a list of text for each unique story identifier in the Model.

        Note that this will be an empty list if the model has to rooms.
        """
        _stories = set()
        for room in self._rooms:
            if room.story is not None:
                _stories.add(room.story)
        return list(_stories)

    @property
    def volume(self):
        """Get the combined volume of all rooms in the Model.

        Note that this property accounts for the room multipliers. Also note that,
        if this model's rooms are not closed solids, the value of this property
        will not be accurate.
        """
        return sum([room.volume * room.multiplier for room in self._rooms])

    @property
    def floor_area(self):
        """Get the combined area of all room floor faces in the Model.

        Note that this property accounts for the room multipliers.
        """
        return sum([room.floor_area * room.multiplier for room in self._rooms
                    if not room.exclude_floor_area])

    @property
    def exposed_area(self):
        """Get the combined area of all room faces with outdoor boundary conditions.

        Useful for estimating infiltration, often expressed as a flow per unit exposed
        envelope area. Note that this property accounts for the room multipliers.
        """
        return sum([room.exposed_area * room.multiplier for room in self._rooms])

    @property
    def exterior_wall_area(self):
        """Get the combined area of all exterior walls on the model's rooms.

        This is NOT the area of the wall's punched_geometry and it includes BOTH
        the area of opaque and transparent parts of the walls. Note that this
        property accounts for the room multipliers.
        """
        return sum([room.exterior_wall_area * room.multiplier for room in self._rooms])

    @property
    def exterior_roof_area(self):
        """Get the combined area of all exterior roofs on the model's rooms.

        This is NOT the area of the roof's punched_geometry and it includes BOTH
        the area of opaque and transparent parts of the roofs. Note that this
        property accounts for the room multipliers.
        """
        return sum([room.exterior_roof_area * room.multiplier for room in self._rooms])

    @property
    def exterior_aperture_area(self):
        """Get the combined area of all exterior apertures on the model's rooms.

        Note that this property accounts for the room multipliers.
        """
        return sum([room.exterior_aperture_area * room.multiplier
                    for room in self._rooms])

    @property
    def exterior_wall_aperture_area(self):
        """Get the combined area of all apertures on exterior walls of the model's rooms.

        Note that this property accounts for the room multipliers.
        """
        return sum([room.exterior_wall_aperture_area * room.multiplier
                    for room in self._rooms])

    @property
    def exterior_skylight_aperture_area(self):
        """Get the combined area of all apertures on exterior roofs of the model's rooms.

        Note that this property accounts for the room multipliers.
        """
        return sum([room.exterior_skylight_aperture_area * room.multiplier
                    for room in self._rooms])

    @property
    def min(self):
        """Get a Point3D for the min bounding box vertex in the XY plane."""
        return self._calculate_min(self._all_objects())

    @property
    def max(self):
        """Get a Point3D for the max bounding box vertex in the XY plane."""
        return self._calculate_max(self._all_objects())

    def add_model(self, other_model):
        """Add another Model object to this model."""
        assert isinstance(other_model, Model), \
            'Expected Model. Got {}.'.format(type(other_model))
        for room in other_model._rooms:
            self._rooms.append(room)
        for face in other_model._orphaned_faces:
            self._orphaned_faces.append(face)
        for shade in other_model._orphaned_shades:
            self._orphaned_shades.append(shade)
        for aperture in other_model._orphaned_apertures:
            self._orphaned_apertures.append(aperture)
        for door in other_model._orphaned_doors:
            self._orphaned_doors.append(door)

    def add_room(self, obj):
        """Add a Room object to the model."""
        assert isinstance(obj, Room), 'Expected Room. Got {}.'.format(type(obj))
        self._rooms.append(obj)

    def add_face(self, obj):
        """Add an orphaned Face object without a parent to the model."""
        assert isinstance(obj, Face), 'Expected Face. Got {}.'.format(type(obj))
        assert not obj.has_parent, 'Face "{}"" has a parent Room. Add the Room to '\
            'the model instead of the Face.'.format(obj.display_name)
        self._orphaned_faces.append(obj)

    def add_aperture(self, obj):
        """Add an orphaned Aperture object to the model."""
        assert isinstance(obj, Aperture), 'Expected Aperture. Got {}.'.format(type(obj))
        assert not obj.has_parent, 'Aperture "{}"" has a parent Face. Add the Face to '\
            'the model instead of the Aperture.'.format(obj.display_name)
        self._orphaned_apertures.append(obj)

    def add_door(self, obj):
        """Add an orphaned Door object to the model."""
        assert isinstance(obj, Door), 'Expected Door. Got {}.'.format(type(obj))
        assert not obj.has_parent, 'Door "{}"" has a parent Face. Add the Face to '\
            'the model instead of the Door.'.format(obj.display_name)
        self._orphaned_doors.append(obj)

    def add_shade(self, obj):
        """Add an orphaned Shade object to the model, typically representing context."""
        assert isinstance(obj, Shade), 'Expected Shade. Got {}.'.format(type(obj))
        assert not obj.has_parent, 'Shade "{}"" has a parent object. Add the object to '\
            'the model instead of the Shade.'.format(obj.display_name)
        self._orphaned_shades.append(obj)

    def remove_rooms(self):
        """Remove all Rooms from the model."""
        self._rooms = []

    def remove_faces(self):
        """Remove all orphaned Faces from the model."""
        self._orphaned_faces = []

    def remove_apertures(self):
        """Remove all orphaned Apertures from the model."""
        self._orphaned_apertures = []

    def remove_doors(self):
        """Remove all orphaned Doors from the model."""
        self._orphaned_doors = []

    def remove_shades(self):
        """Remove all orphaned Shades from the model, typically representing context."""
        self._orphaned_shades = []

    def remove_assigned_apertures(self):
        """Remove all Apertures assigned to the model's Faces.

        This includes nested apertures like those assigned to Faces with parent Rooms.
        """
        for room in self._rooms:
            for face in room.faces:
                face.remove_apertures()
        for face in self._orphaned_faces:
            face.remove_apertures()

    def remove_assigned_doors(self):
        """Remove all Doors assigned to the model's Faces.

        This includes nested doors like those assigned to Faces with parent Rooms.
        """
        for room in self._rooms:
            for face in room.faces:
                face.remove_doors()
        for face in self._orphaned_faces:
            face.remove_doors()

    def remove_assigned_shades(self):
        """Remove all Shades assigned to the model's Rooms, Faces, Apertures and Doors.

        This includes nested shades like those assigned to Apertures with parent
        Faces that have parent Rooms.
        """
        for room in self._rooms:
            room.remove_shades()
            for face in room.faces:
                face.remove_shades()
                for ap in face.apertures:
                    ap.remove_shades()
                for dr in face.doors:
                    dr.remove_shades()
        for face in self._orphaned_faces:
            face.remove_shades()
            for ap in face.apertures:
                ap.remove_shades()
            for dr in face.doors:
                dr.remove_shades()
        for aperture in self._orphaned_apertures:
            aperture.remove_shades()
        for door in self._orphaned_doors:
            door.remove_shades()

    def remove_all_apertures(self):
        """Remove all Apertures from the model.

        This includes assigned apertures as well as orphaned apertures.
        """
        self.remove_apertures()
        self.remove_assigned_apertures()

    def remove_all_doors(self):
        """Remove all Doors from the model.

        This includes assigned doors as well as orphaned doors.
        """
        self.remove_doors()
        self.remove_assigned_doors()

    def remove_all_shades(self):
        """Remove all Shades from the model.

        This includes assigned shades as well as orphaned shades.
        """
        self.remove_shades()
        self.remove_assigned_shades()

    def rooms_by_identifier(self, identifiers):
        """Get a list of Room objects in the model given the Room identifiers."""
        rooms, missing_ids = [], []
        model_rooms = self._rooms
        for obj_id in identifiers:
            for room in model_rooms:
                if room.identifier == obj_id:
                    rooms.append(room)
                    break
            else:
                missing_ids.append(obj_id)
        if len(missing_ids) != 0:
            all_objs = ' '.join(['"' + rid + '"' for rid in missing_ids])
            raise ValueError(
                'The following Rooms were not found in the model: {}'.format(all_objs)
            )
        return rooms

    def faces_by_identifier(self, identifiers):
        """Get a list of Face objects in the model given the Face identifiers."""
        faces, missing_ids = [], []
        model_faces = self.faces
        for obj_id in identifiers:
            for face in model_faces:
                if face.identifier == obj_id:
                    faces.append(face)
                    break
            else:
                missing_ids.append(obj_id)
        if len(missing_ids) != 0:
            all_objs = ' '.join(['"' + rid + '"' for rid in missing_ids])
            raise ValueError(
                'The following Faces were not found in the model: {}'.format(all_objs)
            )
        return faces

    def apertures_by_identifier(self, identifiers):
        """Get a list of Aperture objects in the model given the Aperture identifiers."""
        apertures, missing_ids = [], []
        model_apertures = self.apertures
        for obj_id in identifiers:
            for aperture in model_apertures:
                if aperture.identifier == obj_id:
                    apertures.append(aperture)
                    break
            else:
                missing_ids.append(obj_id)
        if len(missing_ids) != 0:
            all_objs = ' '.join(['"' + rid + '"' for rid in missing_ids])
            raise ValueError(
                'The following Apertures were not found in the model: {}'.format(all_objs)
            )
        return apertures

    def doors_by_identifier(self, identifiers):
        """Get a list of Door objects in the model given the Door identifiers."""
        doors, missing_ids = [], []
        model_doors = self.doors
        for obj_id in identifiers:
            for door in model_doors:
                if door.identifier == obj_id:
                    doors.append(door)
                    break
            else:
                missing_ids.append(obj_id)
        if len(missing_ids) != 0:
            all_objs = ' '.join(['"' + rid + '"' for rid in missing_ids])
            raise ValueError(
                'The following Doors were not found in the model: {}'.format(all_objs)
            )
        return doors

    def shades_by_identifier(self, identifiers):
        """Get a list of Shade objects in the model given the Shade identifiers."""
        shades, missing_ids = [], []
        model_shades = self.shades
        for obj_id in identifiers:
            for face in model_shades:
                if face.identifier == obj_id:
                    shades.append(face)
                    break
            else:
                missing_ids.append(obj_id)
        if len(missing_ids) != 0:
            all_objs = ' '.join(['"' + rid + '"' for rid in missing_ids])
            raise ValueError(
                'The following Shades were not found in the model: {}'.format(all_objs)
            )
        return shades

    def add_prefix(self, prefix):
        """Change the identifier of this object and child objects by inserting a prefix.

        This is particularly useful in workflows where you duplicate and edit
        a starting object and then want to combine it with the original object
        since all objects within a Model must have unique identifiers.

        Args:
            prefix: Text that will be inserted at the start of this object's
                (and child objects') identifier and display_name. It is recommended
                that this prefix be short to avoid maxing out the 100 allowable
                characters for honeybee identifiers.
        """
        for room in self._rooms:
            room.add_prefix(prefix)
        for face in self._orphaned_faces:
            face.add_prefix(prefix)
        for shade in self._orphaned_shades:
            shade.add_prefix(prefix)
        for aperture in self._orphaned_apertures:
            aperture.add_prefix(prefix)
        for door in self._orphaned_doors:
            door.add_prefix(prefix)

    def move(self, moving_vec):
        """Move this Model along a vector.

        Args:
            moving_vec: A ladybug_geometry Vector3D with the direction and distance
                to move the Model.
        """
        for room in self._rooms:
            room.move(moving_vec)
        for face in self._orphaned_faces:
            face.move(moving_vec)
        for shade in self._orphaned_shades:
            shade.move(moving_vec)
        for aperture in self._orphaned_apertures:
            aperture.move(moving_vec)
        for door in self._orphaned_doors:
            door.move(moving_vec)
        self.properties.move(moving_vec)

    def rotate(self, axis, angle, origin):
        """Rotate this Model by a certain angle around an axis and origin.

        Args:
            axis: A ladybug_geometry Vector3D axis representing the axis of rotation.
            angle: An angle for rotation in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        for room in self._rooms:
            room.rotate(axis, angle, origin)
        for face in self._orphaned_faces:
            face.rotate(axis, angle, origin)
        for shade in self._orphaned_shades:
            shade.rotate(axis, angle, origin)
        for aperture in self._orphaned_apertures:
            aperture.rotate(axis, angle, origin)
        for door in self._orphaned_doors:
            door.rotate(axis, angle, origin)
        self.properties.rotate(axis, angle, origin)

    def rotate_xy(self, angle, origin):
        """Rotate this Model counterclockwise in the world XY plane by a certain angle.

        Args:
            angle: An angle in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        for room in self._rooms:
            room.rotate_xy(angle, origin)
        for face in self._orphaned_faces:
            face.rotate_xy(angle, origin)
        for shade in self._orphaned_shades:
            shade.rotate_xy(angle, origin)
        for aperture in self._orphaned_apertures:
            aperture.rotate_xy(angle, origin)
        for door in self._orphaned_doors:
            door.rotate_xy(angle, origin)
        self.properties.rotate_xy(angle, origin)

    def reflect(self, plane):
        """Reflect this Model across a plane with the input normal vector and origin.

        Args:
            plane: A ladybug_geometry Plane across which the object will
                be reflected.
        """
        for room in self._rooms:
            room.reflect(plane)
        for face in self._orphaned_faces:
            face.reflect(plane)
        for shade in self._orphaned_shades:
            shade.reflect(plane)
        for aperture in self._orphaned_apertures:
            aperture.reflect(plane)
        for door in self._orphaned_doors:
            door.reflect(plane)
        self.properties.reflect(plane)

    def scale(self, factor, origin=None):
        """Scale this Model by a factor from an origin point.

        Note that using this method does NOT scale the model tolerance and, if
        it is desired that this tolerance be scaled with the model geometry,
        it must be scaled separately.

        Args:
            factor: A number representing how much the object should be scaled.
            origin: A ladybug_geometry Point3D representing the origin from which
                to scale. If None, it will be scaled from the World origin (0, 0, 0).
        """
        for room in self._rooms:
            room.scale(factor, origin)
        for face in self._orphaned_faces:
            face.scale(factor, origin)
        for shade in self._orphaned_shades:
            shade.scale(factor, origin)
        for aperture in self._orphaned_apertures:
            aperture.scale(factor, origin)
        for door in self._orphaned_doors:
            door.scale(factor, origin)
        self.properties.scale(factor, origin)

    def wall_apertures_by_ratio(self, ratio, tolerance=0.01):
        """Add apertures to all exterior walls given a ratio of aperture to face area.

        Note this method only affects the Models rooms (no orphaned faces) and it
        removes any existing apertures and doors on the room's exterior walls.
        This method attempts to generate as few apertures as necessary to meet the ratio.

        Args:
            ratio: A number between 0 and 1 (but not perfectly equal to 1)
                for the desired ratio between aperture area and face area.
            tolerance: The maximum difference between point values for them to be
                considered a part of a rectangle. This is used in the event that
                this face is concave and an attempt to subdivide the face into a
                rectangle is made. It does not affect the ability to produce apertures
                for convex Faces. Default: 0.01, suitable for objects in meters.
        """
        for room in self._rooms:
            room.wall_apertures_by_ratio(ratio, tolerance)

    def skylight_apertures_by_ratio(self, ratio, tolerance=0.01):
        """Add apertures to all exterior roofs given a ratio of aperture to face area.

        Note this method only affects the Models rooms (no orphaned faces) and
        removes any existing apertures and overhead doors on the Room's roofs.
        This method attempts to generate as few apertures as necessary to meet the ratio.

        Args:
            ratio: A number between 0 and 1 (but not perfectly equal to 1)
                for the desired ratio between aperture area and face area.
            tolerance: The maximum difference between point values for them to be
                considered a part of a rectangle. This is used in the event that
                this face is concave and an attempt to subdivide the face into a
                rectangle is made. It does not affect the ability to produce apertures
                for convex Faces. Default: 0.01, suitable for objects in meters.
        """
        for room in self._rooms:
            room.skylight_apertures_by_ratio(ratio, tolerance)

    def assign_stories_by_floor_height(self, min_difference=2.0, overwrite=False):
        """Assign story properties to the rooms of this Model using their floor heights.

        Stories will be named with a standard convention ('Floor1', 'Floor2', etc.).

        Args:
            min_difference: An float value to denote the minimum difference
                in floor heights that is considered meaningful. This can be used
                to ensure rooms like those representing stair landings are grouped
                with floors. Default: 2.0, which means that any difference in
                floor heights less than 2.0 will be considered a part of the
                same story. This assumption is suitable for models in meters.
            overwrite: If True, all story properties of this model's rooms will
                be overwritten by this method. If False, this method will only
                assign stories to Rooms that do not already have a story identifier
                already assigned to them. (Default: False).

        Returns:
            A list of the unique story names that were assigned to the input rooms.
        """
        if overwrite:
            for room in self._rooms:
                room.story = None
        return Room.stories_by_floor_height(self._rooms, min_difference)

    def convert_to_units(self, units='Meters'):
        """Convert all of the geometry in this model to certain units.

        This involves scaling the geometry, scaling the Model tolerance, and
        changing the Model's units property.

        Args:
            units: Text for the units to which the Model geometry should be
                converted. Default: Meters. Choose from the following:

                * Meters
                * Millimeters
                * Feet
                * Inches
                * Centimeters
        """
        if self.units != units:
            scale_fac1 = conversion_factor_to_meters(self.units)
            scale_fac2 = conversion_factor_to_meters(units)
            scale_fac = scale_fac1 / scale_fac2
            self.scale(scale_fac)
            self.tolerance = self.tolerance * scale_fac
            self.units = units

    def check_all(self, raise_exception=True, detailed=False):
        """Check all of the aspects of the Model for possible errors.

        This includes basic properties like adjacency checks and all geometry checks.
        Furthermore, all extension attributes will be checked assuming the extension
        Model properties have a check_all function. Note that an exception will
        always be raised if the model has a tolerance of zero as this means that
        no geometry checks can be performed.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if any Model errors are found. If False, this method will simply
                return a text string with all errors that were found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A text string with all errors that were found or a list if detailed is True.
            This string (or list) will be empty if no errors were found.
        """
        # set up defaults to ensure the method runs correctly
        detailed = False if raise_exception else detailed
        msgs = []
        # check that a tolerance has been specified in the model
        assert self.tolerance != 0, \
            'Model must have a non-zero tolerance in order to perform geometry checks.'
        assert self.angle_tolerance != 0, \
            'Model must have a non-zero angle_tolerance to perform geometry checks.'
        tol = self.tolerance
        ang_tol = self.angle_tolerance
        # perform checks for key honeybee model schema rules
        msgs.append(self.check_duplicate_room_identifiers(False, detailed))
        msgs.append(self.check_duplicate_face_identifiers(False, detailed))
        msgs.append(self.check_duplicate_sub_face_identifiers(False, detailed))
        msgs.append(self.check_duplicate_shade_identifiers(False, detailed))
        msgs.append(self.check_missing_adjacencies(False, detailed))
        msgs.append(self.check_matching_adjacent_areas(tol, False, detailed))
        msgs.append(self.check_all_air_boundaries_adjacent(False, detailed))
        msgs.append(self.check_rooms_all_air_boundary(False, detailed))
        # perform several checks for Face3D geometry rules
        msgs.append(self.check_self_intersecting(tol, False, detailed))
        msgs.append(self.check_planar(tol, False, detailed))
        # remove colinear vertices to ensure that this doesn't create faces with <3 edges
        for room in self.rooms:
            try:
                new_room = room.duplicate()  # duplicate to avoid editing the original
                new_room.remove_colinear_vertices_envelope(tol)
            except ValueError as e:
                deg_msg = str(e)
                if detailed:
                    deg_msg = [{
                        'type': 'ValidationError',
                        'code': '000107',
                        'error_type': 'Degenerate Geometry Error',
                        'extension_type': 'Core',
                        'element_type': 'Room',
                        'element_id': room.identifier,
                        'element_name': room.display_name,
                        'message': deg_msg
                    }]
                msgs.append(deg_msg)
        # perform geometry checks related to parent-child relationships
        msgs.append(self.check_sub_faces_valid(tol, ang_tol, False, detailed))
        msgs.append(self.check_sub_faces_overlapping(False, detailed))
        msgs.append(self.check_rooms_solid(tol, ang_tol, False, detailed))
        # check the extension attributes
        ext_msgs = self._properties._check_extension_attr(detailed)
        if detailed:
            ext_msgs = [m for m in ext_msgs if isinstance(m, list)]
        msgs.extend(ext_msgs)

        # output a final report of errors or raise an exception
        full_msgs = [msg for msg in msgs if msg]
        if detailed:
            return [m for msg in full_msgs for m in msg]
        full_msg = '\n'.join(full_msgs)
        if raise_exception and len(full_msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def check_duplicate_room_identifiers(self, raise_exception=True, detailed=False):
        """Check that there are no duplicate Room identifiers in the model.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if duplicate identifiers are found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        return check_duplicate_identifiers(
            self._rooms, raise_exception, 'Room', detailed, '000004', 'Core',
            'Duplicate Room Identifier')

    def check_duplicate_face_identifiers(self, raise_exception=True, detailed=False):
        """Check that there are no duplicate Face identifiers in the model.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if duplicate identifiers are found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        return check_duplicate_identifiers_parent(
            self.faces, raise_exception, 'Face', detailed, '000003', 'Core',
            'Duplicate Face Identifier')

    def check_duplicate_sub_face_identifiers(self, raise_exception=True, detailed=False):
        """Check that there are no duplicate sub-face identifiers in the model.

        Note that both Apertures and Doors are checked for duplicates since the two
        are counted together by EnergyPlus.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if duplicate identifiers are found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        sub_faces = self.apertures + self.doors
        return check_duplicate_identifiers_parent(
            sub_faces, raise_exception, 'sub-face', detailed, '000002', 'Core',
            'Duplicate Sub-Face Identifier')

    def check_duplicate_shade_identifiers(self, raise_exception=True, detailed=False):
        """Check that there are no duplicate Shade identifiers in the model.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if duplicate identifiers are found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        return check_duplicate_identifiers_parent(
            self.shades, raise_exception, 'Shade', detailed, '000001', 'Core',
            'Duplicate Shade Identifier')

    def check_missing_adjacencies(self, raise_exception=True, detailed=False):
        """Check that all Faces Apertures, and Doors have adjacent objects in the model.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if invalid adjacencies are found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        detailed = False if raise_exception else detailed
        # loop through all objects and get their adjacent object
        room_ids = []
        face_bc_ids, face_set = [], set()
        ap_bc_ids, ap_set = [], set()
        door_bc_ids, dr_set = [], set()
        sr = []
        for room in self._rooms:
            for face in room._faces:
                if isinstance(face.boundary_condition, Surface):
                    sr.append(self._self_adj_check(
                        'Face', face, face_bc_ids, room_ids, face_set, detailed))
                    for ap in face.apertures:
                        assert isinstance(ap.boundary_condition, Surface), \
                            'Aperture "{}" must have Surface boundary condition ' \
                            'if the parent Face has a Surface BC.'.format(ap.full_id)
                        sr.append(self._self_adj_check(
                            'Aperture', ap, ap_bc_ids, room_ids, ap_set, detailed))
                    for dr in face.doors:
                        assert isinstance(dr.boundary_condition, Surface), \
                            'Door "{}" must have Surface boundary condition ' \
                            'if the parent Face has a Surface BC.'.format(dr.full_id)
                        sr.append(self._self_adj_check(
                            'Door', dr, door_bc_ids, room_ids, dr_set, detailed))
        # check to see if the adjacent objects are in the model
        mr = self._missing_adj_check(self.rooms_by_identifier, room_ids)
        mf = self._missing_adj_check(self.faces_by_identifier, face_bc_ids)
        ma = self._missing_adj_check(self.apertures_by_identifier, ap_bc_ids)
        md = self._missing_adj_check(self.doors_by_identifier, door_bc_ids)
        # if not, go back and find the original object with the missing BC object
        msgs = []
        if len(mr) != 0 or len(mf) != 0 or len(ma) != 0 or len(md) != 0:
            for room in self._rooms:
                for face in room._faces:
                    if isinstance(face.boundary_condition, Surface):
                        bc_obj, bc_room = self._adj_objects(face)
                        if bc_obj in mf:
                            self._missing_adj_msg(
                                msgs, face, bc_obj, 'Face', 'Face', detailed)
                        if bc_room in mr:
                            self._missing_adj_msg(
                                msgs, face, bc_room, 'Face', 'Room', detailed)
                        for ap in face.apertures:
                            bc_obj, bc_room = self._adj_objects(ap)
                            if bc_obj in ma:
                                self._missing_adj_msg(
                                    msgs, ap, bc_obj, 'Aperture', 'Aperture', detailed)
                            if bc_room in mr:
                                self._missing_adj_msg(
                                    msgs, ap, bc_room, 'Aperture', 'Room', detailed)
                        for dr in face.doors:
                            bc_obj, bc_room = self._adj_objects(dr)
                            if bc_obj in ma:
                                self._missing_adj_msg(
                                    msgs, dr, bc_obj, 'Door', 'Door', detailed)
                            if bc_room in mr:
                                self._missing_adj_msg(
                                    msgs, dr, bc_room, 'Door', 'Room', detailed)
        # return the final error messages
        all_msgs = [m for m in sr + msgs if m]
        if detailed:
            return [m for msg in all_msgs for m in msg]
        msg = '\n'.join(all_msgs)
        if msg != '' and raise_exception:
            raise ValueError(msg)
        return msg

    def check_matching_adjacent_areas(self, tolerance=0.01, raise_exception=True,
                                      detailed=False):
        """Check that all adjacent Faces have areas that match within the tolerance.

        This is required for energy simulation in order to get matching heat flow
        across adjacent Faces. Otherwise, conservation of energy is violated.
        Note that, if there are missing adjacencies in the model, the message from
        this method will simply note this fact without reporting on mis-matched areas.

        Args:
            tolerance: tolerance: The maximum difference between x, y, and z values
                at which face vertices are considered equivalent. (Default: 0.01,
                suitable for objects in meters).
            raise_exception: Boolean to note whether a ValueError should be raised
                if invalid adjacencies are found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        detailed = False if raise_exception else detailed
        # first gather all interior faces in the model and their adjacent object
        base_faces, adj_ids = [], []
        for room in self._rooms:
            for face in room._faces:
                if isinstance(face.boundary_condition, Surface):
                    base_faces.append(face)
                    adj_ids.append(face.boundary_condition.boundary_condition_object)
        # get the adjacent faces
        try:
            adj_faces = self.faces_by_identifier(adj_ids)
        except ValueError as e:  # the model has missing adjacencies
            if detailed:  # the user will get a more detailed error in honeybee-core
                return []
            else:
                msg = 'Matching adjacent areas could not be verified because ' \
                    'of missing adjacencies in the model.  \n{}'.format(e)
                if raise_exception:
                    raise ValueError(msg)
                return msg
        # loop through the adjacent face pairs and report if areas are not matched
        full_msgs = []
        for base_f, adj_f in zip(base_faces, adj_faces):
            tol_area = math.sqrt(base_f.area) * tolerance
            if abs(base_f.area - adj_f.area) > tol_area:
                f_msg = 'Face "{}" with area {} is adjacent to Face "{}" with area {}.' \
                    ' This difference is greater than the tolerance of {}.'.format(
                        base_f.full_id, base_f.area, adj_f.full_id, adj_f.area, tolerance
                    )
                f_msg = self._validation_message_child(
                    f_msg, adj_f, detailed, '000205',
                    error_type='Mismatched Area Adjacency')
                full_msgs.append(f_msg)
        full_msg = full_msgs if detailed else '\n'.join(full_msgs)
        if raise_exception and len(full_msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def check_all_air_boundaries_adjacent(self, raise_exception=True, detailed=False):
        """Check that all Faces with the AirBoundary type are adjacent to other Faces.

        This is a requirement for energy simulation.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if an AirBoundary without an adjacency is found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        detailed = False if raise_exception else detailed
        msgs = []
        for face in self.faces:
            if isinstance(face.type, AirBoundary) and not \
                    isinstance(face.boundary_condition, Surface):
                msg = 'Face "{}" is an AirBoundary but is not adjacent ' \
                      'to another Face.'.format(face.full_id)
                msg = self._validation_message_child(
                    msg, face, detailed, '000206', error_type='Non-Adjacent AirBoundary')
                msgs.append(msg)
        if detailed:
            return msgs
        full_msg = '\n'.join(msgs)
        if raise_exception and len(msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def check_rooms_all_air_boundary(self, raise_exception=True, detailed=False):
        """Check that there are no Rooms composed entirely of AirBoundaries.

        This is a requirement for energy simulation since EnergyPlus will throw
        a "no surfaces" error if it encounters a Room composed entirely of
        AirBoundaries.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if a Room composed entirely of AirBoundaries is found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        detailed = False if raise_exception else detailed
        msgs = []
        for room in self._rooms:
            if all(isinstance(f.type, AirBoundary) for f in room._faces):
                msg = 'Room "{}" is composed entirely of AirBoundary Faces. It ' \
                    'should be merged with adjacent rooms.'.format(room.full_id)
                msg = self._validation_message_child(
                    msg, room, detailed, '000207',
                    error_type='Room Composed Entirely of AirBoundaries')
                msgs.append(msg)
        if detailed:
            return msgs
        full_msg = '\n'.join(msgs)
        if raise_exception and len(msgs) != 0:
            raise ValueError(full_msg)
        return full_msg


    def check_rooms_solid(self, tolerance=0.01, angle_tolerance=1,
                          raise_exception=True, detailed=False):
        """Check whether the Model's rooms are closed solid to within tolerances.

        Args:
            tolerance: tolerance: The maximum difference between x, y, and z values
                at which face vertices are considered equivalent. Default: 0.01,
                suitable for objects in meters.
            angle_tolerance: The max angle difference in degrees that vertices are
                allowed to differ from one another in order to consider them colinear.
                Default: 1 degree.
            raise_exception: Boolean to note whether a ValueError should be raised
                if the room geometry does not form a closed solid. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        detailed = False if raise_exception else detailed
        msgs = []
        for room in self._rooms:
            msg = room.check_solid(tolerance, angle_tolerance, False, detailed)
            if detailed:
                msgs.extend(msg)
            elif msg != '':
                msgs.append(msg)
        if detailed:
            return msgs
        full_msg = '\n'.join(msgs)
        if raise_exception and len(msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def check_sub_faces_valid(self, tolerance=0.01, angle_tolerance=1,
                              raise_exception=True, detailed=False):
        """Check that model's sub-faces are co-planar with faces and in the face boundary.

        Note this does not check the planarity of the sub-faces themselves, whether
        they self-intersect, or whether they have a non-zero area.

        Args:
            tolerance: The minimum difference between the coordinate values of two
                vertices at which they can be considered equivalent. Default: 0.01,
                suitable for objects in meters.
            angle_tolerance: The max angle in degrees that the plane normals can
                differ from one another in order for them to be considered coplanar.
                Default: 1 degree.
            raise_exception: Boolean to note whether a ValueError should be raised
                if an sub-face is not valid. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        detailed = False if raise_exception else detailed
        msgs = []
        for rm in self._rooms:
            msg = rm.check_sub_faces_valid(tolerance, angle_tolerance, False, detailed)
            if detailed:
                msgs.extend(msg)
            elif msg != '':
                msgs.append(msg)
        for f in self._orphaned_faces:
            msg = f.check_sub_faces_valid(tolerance, angle_tolerance, False, detailed)
            if detailed:
                msgs.extend(msg)
            elif msg != '':
                msgs.append(msg)
        if detailed:
            return msgs
        full_msg = '\n'.join(msgs)
        if raise_exception and len(msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def check_sub_faces_overlapping(self, raise_exception=True, detailed=False):
        """Check that model's sub-faces do not overlap with one another.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if a sub-faces overlap with one another.
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        detailed = False if raise_exception else detailed
        msgs = []
        for rm in self._rooms:
            msg = rm.check_sub_faces_overlapping(False, detailed)
            if detailed:
                msgs.extend(msg)
            elif msg != '':
                msgs.append(msg)
        for f in self._orphaned_faces:
            msg = f.check_sub_faces_overlapping(False, detailed)
            if detailed:
                msgs.extend(msg)
            elif msg != '':
                msgs.append(msg)
        if detailed:
            return msgs
        full_msg = '\n'.join(msgs)
        if raise_exception and len(msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def check_planar(self, tolerance, raise_exception=True, detailed=False):
        """Check that all of the Model's geometry components are planar.

        This includes all of the Model's Faces, Apertures, Doors and Shades.

        Args:
            tolerance: The minimum distance between a given vertex and a the
                object's plane at which the vertex is said to lie in the plane.
            raise_exception: Boolean to note whether an ValueError should be
                raised if a vertex does not lie within the object's plane.
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        detailed = False if raise_exception else detailed
        msgs = []
        for face in self.faces:
            msgs.append(face.check_planar(tolerance, False, detailed))
        for shd in self.shades:
            msgs.append(shd.check_planar(tolerance, False, detailed))
        for ap in self.apertures:
            msgs.append(ap.check_planar(tolerance, False, detailed))
        for dr in self.doors:
            msgs.append(dr.check_planar(tolerance, False, detailed))
        full_msgs = [msg for msg in msgs if msg]
        if detailed:
            return [m for msg in full_msgs for m in msg]
        full_msg = '\n'.join(full_msgs)
        if raise_exception and len(full_msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def check_self_intersecting(self, tolerance=0.01, raise_exception=True,
                                detailed=False):
        """Check that no edges of the Model's geometry components self-intersect.

        This includes all of the Model's Faces, Apertures, Doors and Shades.

        Args:
            tolerance: The minimum difference between the coordinate values of two
                vertices at which they can be considered equivalent. Default: 0.01,
                suitable for objects in meters.
            raise_exception: If True, a ValueError will be raised if an object
                intersects with itself (like a bowtie). (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        detailed = False if raise_exception else detailed
        msgs = []
        for room in self.rooms:
            msgs.append(room.check_self_intersecting(tolerance, False, detailed))
        for face in self.orphaned_faces:
            msgs.append(face.check_self_intersecting(tolerance, False, detailed))
        for shd in self.orphaned_shades:
            msgs.append(shd.check_self_intersecting(tolerance, False, detailed))
        for ap in self.orphaned_apertures:
            msgs.append(ap.check_self_intersecting(tolerance, False, detailed))
        for dr in self.orphaned_doors:
            msgs.append(dr.check_self_intersecting(tolerance, False, detailed))
        full_msgs = [msg for msg in msgs if msg]
        if detailed:
            return [m for msg in full_msgs for m in msg]
        full_msg = '\n'.join(full_msgs)
        if raise_exception and len(full_msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def check_non_zero(self, tolerance=0.0001, raise_exception=True, detailed=False):
        """Check that the Model's geometry components are above a "zero" area tolerance.

        This includes all of the Model's Faces, Apertures, Doors and Shades.

        Args:
            tolerance: The minimum acceptable area of the object. Default is 0.0001,
                which is equal to 1 cm2 when model units are meters. This is just
                above the smallest size that OpenStudio will accept.
            raise_exception: If True, a ValueError will be raised if the object
                area is below the tolerance. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        detailed = False if raise_exception else detailed
        msgs = []
        for face in self.faces:
            msgs.append(face.check_non_zero(tolerance, False, detailed))
        for shd in self.shades:
            msgs.append(shd.check_non_zero(tolerance, False, detailed))
        for ap in self.apertures:
            msgs.append(ap.check_non_zero(tolerance, False, detailed))
        for dr in self.doors:
            msgs.append(dr.check_non_zero(tolerance, False, detailed))
        full_msgs = [msg for msg in msgs if msg]
        if detailed:
            return [m for msg in full_msgs for m in msg]
        full_msg = '\n'.join(full_msgs)
        if raise_exception and len(full_msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def triangulated_apertures(self):
        """Get triangulated versions of the model Apertures that have more than 4 sides.

        This is necessary for energy simulation since EnergyPlus cannot accept
        sub-faces with more than 4 sides. Note that this method does not alter the
        Apertures within the Model object but just returns a list of modified
        Apertures that all have 3 or 4 sides.

        Returns:
            A tuple with two elements

            -   triangulated_apertures: A list of lists where each list is a set of
                triangle Apertures meant to replace an Aperture with more than
                4 sides in the model.

            -   parents_to_edit: An list of lists that parallels the triangulated
                apertures in that each item represents an Aperture that has been
                triangulated in the model. However, each of these lists holds between
                1 and 3 values for the identifiers of the original aperture and parents
                of the aperture. This information is intended to help edit parent
                faces that have had their child faces triangulated. The 3 values
                are as follows:

                * 0 = The identifier of the original Aperture that was triangulated.
                * 1 = The identifier of the parent Face of the original Aperture
                  (if it exists).
                * 2 = The identifier of the parent Room of the parent Face of the
                  original Aperture (if it exists).
        """
        triangulated_apertures = []
        parents_to_edit = []
        all_apertures = self.apertures
        adj_check = []  # confirms when interior apertures are triangulated by adjacency
        for ap in all_apertures:
            if len(ap.geometry) <= 4:
                pass
            elif ap.identifier not in adj_check:
                # generate the new triangulated apertures
                ap_mesh3d = ap.triangulated_mesh3d
                new_verts = [[ap_mesh3d[v] for v in face] for face in ap_mesh3d.faces]
                new_ap_geo = [Face3D(verts, ap.geometry.plane) for verts in new_verts]
                new_ap_geo = self._remove_sliver_geometries(new_ap_geo)
                new_aps, parent_edit_info = self._replace_aperture(ap, new_ap_geo)
                triangulated_apertures.append(new_aps)
                if parent_edit_info is not None:
                    parents_to_edit.append(parent_edit_info)
                # coordinate new apertures with any adjacent apertures
                if isinstance(ap.boundary_condition, Surface):
                    bc_obj_identifier = ap.boundary_condition.boundary_condition_object
                    for other_ap in all_apertures:
                        if other_ap.identifier == bc_obj_identifier:
                            adj_ap = other_ap
                            break
                    new_adj_ap_geo = [face.flip() for face in new_ap_geo]
                    new_adj_aps, edit_in = self._replace_aperture(adj_ap, new_adj_ap_geo)
                    for new_ap, new_adj_ap in zip(new_aps, new_adj_aps):
                        new_ap.set_adjacency(new_adj_ap)
                    triangulated_apertures.append(new_adj_aps)
                    if edit_in is not None:
                        parents_to_edit.append(edit_in)
                    adj_check.append(adj_ap.identifier)
        return triangulated_apertures, parents_to_edit

    def triangulated_doors(self):
        """Get triangulated versions of the model Doors that have more than 4 sides.

        This is necessary for energy simulation since EnergyPlus cannot accept
        sub-faces with more than 4 sides. Note that this method does not alter the
        Doors within the Model object but just returns a list of Doors that
        all have 3 or 4 sides.

        Returns:
            A tuple with two elements

            -   triangulated_doors: A list of lists where each list is a set of triangle
                Doors meant to replace a Door with more than 4 sides in the model.

            -   parents_to_edit: An list of lists that parellels the triangulated_doors
                in that each item represents a Door that has been triangulated
                in the model. However, each of these lists holds between 1 and 3 values
                for the identifiers of the original door and parents of the door.
                This information is intended to help edit parent faces that have had
                their child faces triangulated. The 3 values are as follows:

                * 0 = The identifier of the original Door that was triangulated.
                * 1 = The identifier of the parent Face of the original Door
                  (if it exists).
                * 2 = The identifier of the parent Room of the parent Face of the
                  original Door (if it exists).
        """
        triangulated_doors = []
        parents_to_edit = []
        all_doors = self.doors
        adj_check = []  # confirms when interior doors are triangulated by adjacency
        for dr in all_doors:
            if len(dr.geometry) <= 4:
                pass
            elif dr.identifier not in adj_check:
                # generate the new triangulated doors
                dr_mesh3d = dr.triangulated_mesh3d
                new_verts = [[dr_mesh3d[v] for v in face] for face in dr_mesh3d.faces]
                new_dr_geo = [Face3D(verts, dr.geometry.plane) for verts in new_verts]
                new_dr_geo = self._remove_sliver_geometries(new_dr_geo)
                new_drs, parent_edit_info = self._replace_door(dr, new_dr_geo)
                triangulated_doors.append(new_drs)
                if parent_edit_info is not None:
                    parents_to_edit.append(parent_edit_info)
                # coordinate new doors with any adjacent doors
                if isinstance(dr.boundary_condition, Surface):
                    bc_obj_identifier = dr.boundary_condition.boundary_condition_object
                    for other_dr in all_doors:
                        if other_dr.identifier == bc_obj_identifier:
                            adj_dr = other_dr
                            break
                    new_adj_dr_geo = [face.flip() for face in new_dr_geo]
                    new_adj_drs, edit_in = self._replace_door(adj_dr, new_adj_dr_geo)
                    for new_dr, new_adj_dr in zip(new_drs, new_adj_drs):
                        new_dr.set_adjacency(new_adj_dr)
                    triangulated_doors.append(new_adj_drs)
                    if edit_in is not None:
                        parents_to_edit.append(edit_in)
                    adj_check.append(adj_dr.identifier)
        return triangulated_doors, parents_to_edit

    def _remove_sliver_geometries(self, face3ds):
        """Remove sliver geometries from a list of Face3Ds."""
        clean_face3ds = []
        for face in face3ds:
            try:
                if face.area >= self.tolerance:
                    clean_face3ds.append(face.remove_colinear_vertices(self.tolerance))
            except ValueError:
                pass  # degenerate triangle; remove it
        return clean_face3ds

    def _replace_aperture(self, original_ap, new_ap_geo):
        """Get new Apertures generated from new_ap_geo and the properties of original_ap.

        Note that this method does not re-link the new apertures to new adjacent
        apertures in the model. This must be done with the returned apertures.

        Args:
            original_ap: The original Aperture object from which properties
                are borrowed.
            new_ap_geo: A list of ladybug_geometry Face3D objects that will be used
                to generate the new Aperture objects.

        Returns:
            A tuple with two elements

            -   new_aps: A list of the new Aperture objects.

            -   parent_edit_info: An array of up to 3 values meant to help edit
                parents that have had their child faces triangulated. The 3 values
                are as follows:

                * 0 = The identifier of the original Aperture that was triangulated.
                * 1 = The identifier of the parent Face of the original Aperture
                  (if it exists).
                * 2 = The identifier of the parent Room of the parent Face of the
                  original Aperture (if it exists).
        """
        # make the new Apertures and add them to the model
        new_aps = []
        for i, ap_face in enumerate(new_ap_geo):
            new_ap = Aperture('{}..{}'.format(original_ap.identifier, i),
                              ap_face, None, original_ap.is_operable)
            new_ap._properties = original_ap._properties  # transfer extension properties
            if original_ap.has_parent:
                new_ap._parent = original_ap.parent
            new_aps.append(new_ap)

        # transfer over any child shades to the first triangulated object
        if len(original_ap._indoor_shades) != 0:
            new_shds = [shd.duplicate() for shd in original_ap._indoor_shades]
            new_aps[0].add_indoor_shades(new_shds)
        if len(original_ap._outdoor_shades) != 0:
            new_shds = [shd.duplicate() for shd in original_ap._outdoor_shades]
            new_aps[0].add_outdoor_shades(new_shds)

        # create the parent edit info
        parent_edit_info = [original_ap.identifier]
        if original_ap.has_parent:
            parent_edit_info.append(original_ap.parent.identifier)
            if original_ap.parent.has_parent:
                parent_edit_info.append(original_ap.parent.parent.identifier)
        return new_aps, parent_edit_info

    def _replace_door(self, original_dr, new_dr_geo):
        """Get new Doors generated from new_dr_geo and the properties of original_dr.

        Note that this method does not re-link the new doors to new adjacent
        doors in the model. This must be done with the returned doors.

        Args:
            original_dr: The original Door object from which properties
                are borrowed.
            new_dr_geo: A list of ladybug_geometry Face3D objects that will be used
                to generate the new Door objects.

        Returns:
            A tuple with four elements

            -   new_drs: A list of the new Door objects.

            -   parent_edit_info: An array of up to 3 values meant to help edit
                parents that have had their child faces triangulated. The 3 values
                are as follows:

                * 0 = The identifier of the original Door that was triangulated.
                * 1 = The identifier of the parent Face of the original Door
                  (if it exists).
                * 2 = The identifier of the parent Room of the parent Face of the
                  original Door (if it exists).
        """
        # make the new doors and add them to the model
        new_drs = []
        for i, dr_face in enumerate(new_dr_geo):
            new_dr = Door('{}..{}'.format(original_dr.identifier, i), dr_face)
            new_dr._properties = original_dr._properties  # transfer extension properties
            if original_dr.has_parent:
                new_dr._parent = original_dr.parent
            new_drs.append(new_dr)

        # transfer over any child shades to the first triangulated object
        if len(original_dr._indoor_shades) != 0:
            new_shds = [shd.duplicate() for shd in original_dr._indoor_shades]
            new_drs[0].add_indoor_shades(new_shds)
        if len(original_dr._outdoor_shades) != 0:
            new_shds = [shd.duplicate() for shd in original_dr._outdoor_shades]
            new_drs[0].add_outdoor_shades(new_shds)

        # create the parent edit info
        parent_edit_info = [original_dr.identifier]
        if original_dr.has_parent:
            parent_edit_info.append(original_dr.parent.identifier)
            if original_dr.parent.has_parent:
                parent_edit_info.append(original_dr.parent.parent.identifier)
        return new_drs, parent_edit_info

    @property
    def to(self):
        """Model writer object.

        Use this method to access Writer class to write the model in other formats.

        Usage:

        .. code-block:: python

            model.to.idf(model) -> idf string.
            model.to.radiance(model) -> Radiance string.
        """
        return writer

    def to_dict(self, included_prop=None, triangulate_sub_faces=False,
                include_plane=True):
        """Return Model as a dictionary.

        Args:
            included_prop: List of properties to filter keys that must be included in
                output dictionary. For example ['energy'] will include 'energy' key if
                available in properties to_dict. By default all the keys will be
                included. To exclude all the keys from extensions use an empty list.
            triangulate_sub_faces: Boolean to note whether sub-faces (including
                Apertures and Doors) should be triangulated if they have more than
                4 sides (True) or whether they should be left as they are (False).
                This triangulation is necessary when exporting directly to EnergyPlus
                since it cannot accept sub-faces with more than 4 vertices. Note that
                setting this to True will only triangulate sub-faces with parent Faces
                that also have parent Rooms since orphaned Apertures and Faces are
                not relevant for energy simulation. (Default: False).
            include_plane: Boolean to note wether the planes of the Face3Ds should be
                included in the output. This can preserve the orientation of the
                X/Y axes of the planes but is not required and can be removed to
                keep the dictionary smaller. (Default: True).
        """
        # write all of the geometry objects and their properties
        base = {'type': 'Model'}
        base['identifier'] = self.identifier
        base['display_name'] = self.display_name
        base['units'] = self.units
        base['properties'] = self.properties.to_dict(included_prop)
        if self._rooms != []:
            base['rooms'] = [r.to_dict(True, included_prop, include_plane)
                             for r in self._rooms]
        if self._orphaned_faces != []:
            base['orphaned_faces'] = [f.to_dict(True, included_prop, include_plane)
                                      for f in self._orphaned_faces]
        if self._orphaned_shades != []:
            base['orphaned_shades'] = [shd.to_dict(True, included_prop, include_plane)
                                       for shd in self._orphaned_shades]
        if self._orphaned_apertures != []:
            base['orphaned_apertures'] = [ap.to_dict(True, included_prop, include_plane)
                                          for ap in self._orphaned_apertures]
        if self._orphaned_doors != []:
            base['orphaned_doors'] = [dr.to_dict(True, included_prop, include_plane)
                                      for dr in self._orphaned_doors]
        if self.tolerance != 0:
            base['tolerance'] = self.tolerance
        if self.angle_tolerance != 0:
            base['angle_tolerance'] = self.angle_tolerance

        # triangulate sub-faces if this was requested
        if triangulate_sub_faces:
            apertures, parents_to_edit = self.triangulated_apertures()
            for tri_aps, edit_infos in zip(apertures, parents_to_edit):
                if len(edit_infos) == 3:
                    for room in base['rooms']:
                        if room['identifier'] == edit_infos[2]:
                            break
                    for face in room['faces']:
                        if face['identifier'] == edit_infos[1]:
                            break
                    for i, ap in enumerate(face['apertures']):
                        if ap['identifier'] == edit_infos[0]:
                            break
                    del face['apertures'][i]
                    face['apertures'].extend(
                        [a.to_dict(True, included_prop) for a in tri_aps])
            doors, parents_to_edit = self.triangulated_doors()
            for tri_drs, edit_infos in zip(doors, parents_to_edit):
                if len(edit_infos) == 3:
                    for room in base['rooms']:
                        if room['identifier'] == edit_infos[2]:
                            break
                    for face in room['faces']:
                        if face['identifier'] == edit_infos[1]:
                            break
                    for i, ap in enumerate(face['doors']):
                        if ap['identifier'] == edit_infos[0]:
                            break
                    del face['doors'][i]
                    face['doors'].extend(
                        [dr.to_dict(True, included_prop) for dr in tri_drs])

        # write in the optional keys if they are not None
        if self.user_data is not None:
            base['user_data'] = self.user_data
        if folders.honeybee_schema_version is not None:
            base['version'] = folders.honeybee_schema_version_str

        return base

    def to_hbjson(self, name=None, folder=None, indent=None,
                  included_prop=None, triangulate_sub_faces=False):
        """Write Honeybee model to HBJSON.

        Args:
            name: A text string for the name of the HBJSON file. If None, the model
                identifier wil be used. (Default: None).
            folder: A text string for the directory where the HBJSON will be written.
                If unspecified, the default simulation folder will be used. This
                is usually at "C:\\Users\\USERNAME\\simulation."
            indent: A positive integer to set the indentation used in the resulting
                HBJSON file. (Default: None).
            included_prop: List of properties to filter keys that must be included in
                output dictionary. For example ['energy'] will include 'energy' key if
                available in properties to_dict. By default all the keys will be
                included. To exclude all the keys from extensions use an empty list.
            triangulate_sub_faces: Boolean to note whether sub-faces (including
                Apertures and Doors) should be triangulated if they have more than
                4 sides (True) or whether they should be left as they are (False).
                This triangulation is necessary when exporting directly to EnergyPlus
                since it cannot accept sub-faces with more than 4 vertices. Note that
                setting this to True will only triangulate sub-faces with parent Faces
                that also have parent Rooms since orphaned Apertures and Faces are
                not relevant for energy simulation. (Default: False).
        """
        # create dictionary from the Honeybee Model
        hb_dict = self.to_dict(included_prop=included_prop,
                               triangulate_sub_faces=triangulate_sub_faces)

        # set up a name and folder for the HBJSON
        if name is None:
            name = self.identifier
        file_name = name if name.lower().endswith('.hbjson') or \
            name.lower().endswith('.json') else '{}.hbjson'.format(name)
        folder = folder if folder is not None else folders.default_simulation_folder
        hb_file = os.path.join(folder, file_name)
        # write HBJSON
        with open(hb_file, 'w') as fp:
            json.dump(hb_dict, fp, indent=indent)
        return hb_file

    def to_hbpkl(self, name=None, folder=None, included_prop=None,
                 triangulate_sub_faces=False):
        """Write Honeybee model to compressed pickle file (HBpkl).

        Args:
            name: A text string for the name of the pickle file. If None, the model
                identifier wil be used. (Default: None).
            folder: A text string for the directory where the pickle file will be
                written. If unspecified, the default simulation folder will be used.
                This is usually at "C:\\Users\\USERNAME\\simulation."
            included_prop: List of properties to filter keys that must be included in
                output dictionary. For example ['energy'] will include 'energy' key if
                available in properties to_dict. By default all the keys will be
                included. To exclude all the keys from extensions use an empty list.
            triangulate_sub_faces: Boolean to note whether sub-faces (including
                Apertures and Doors) should be triangulated if they have more than
                4 sides (True) or whether they should be left as they are (False).
                This triangulation is necessary when exporting directly to EnergyPlus
                since it cannot accept sub-faces with more than 4 vertices. Note that
                setting this to True will only triangulate sub-faces with parent Faces
                that also have parent Rooms since orphaned Apertures and Faces are
                not relevant for energy simulation. (Default: False).
        """
        # create dictionary from the Honeybee Model
        hb_dict = self.to_dict(included_prop=included_prop,
                               triangulate_sub_faces=triangulate_sub_faces)

        # set up a name and folder for the HBpkl
        if name is None:
            name = self.identifier
        file_name = name if name.lower().endswith('.hbpkl') or \
            name.lower().endswith('.pkl') else '{}.hbpkl'.format(name)
        folder = folder if folder is not None else folders.default_simulation_folder
        hb_file = os.path.join(folder, file_name)
        # write the Model dictionary into a file
        with open(hb_file, 'wb') as fp:
            pickle.dump(hb_dict, fp)
        return hb_file

    def to_stl(self, name=None, folder=None):
        """Write Honeybee model to an ASCII STL file.

        Note that all geometry is triangulated when it is converted to STL.

        Args:
            name: A text string for the name of the STL file. If None, the model
                identifier wil be used. (Default: None).
            folder: A text string for the directory where the STL will be written.
                If unspecified, the default simulation folder will be used. This
                is usually at "C:\\Users\\USERNAME\\simulation."
        """
        # set up a name and folder for the STL
        if name is None:
            name = self.identifier
        file_name = name if name.lower().endswith('.stl') else '{}.stl'.format(name)
        folder = folder if folder is not None else folders.default_simulation_folder
        hb_file = os.path.join(folder, file_name)

        # collect all of the Face3Ds across the model as triangles and normals
        all_geo = []
        for face in self.faces:
            all_geo.append(face.punched_geometry)
        for ap in self.apertures:
            all_geo.append(ap.geometry)
        for dr in self.doors:
            all_geo.append(dr.geometry)
        for shd in self.doors:
            all_geo.append(shd.geometry)

        # convert the Face3Ds into a format for export to STL
        _face_vertices, _face_normals = [], []
        for face_3d in all_geo:
            # add the geometry of a Face3D to the lists for STL export
            if len(face_3d) == 3:
                _face_vertices.append(face_3d.vertices)
                _face_normals.append(face_3d.normal)
            else:
                tri_mesh = face_3d.triangulated_mesh3d
                for m_fac in tri_mesh.face_vertices:
                    _face_vertices.append(m_fac)
                    _face_normals.append(face_3d.normal)

        # write the geometry into an STL file
        stl_obj = STL(_face_vertices, _face_normals, self.identifier)
        return stl_obj.to_file(folder, name)

    def _all_objects(self):
        """Get a single list of all the Honeybee objects in a Model."""
        return self._rooms + self._orphaned_faces + self._orphaned_shades + \
            self._orphaned_apertures + self._orphaned_doors

    @staticmethod
    def conversion_factor_to_meters(units):
        """Get the conversion factor to meters based on input units.

        Args:
            units: Text for the units. Choose from the following:

                * Meters
                * Millimeters
                * Feet
                * Inches
                * Centimeters

        Returns:
            A number for the conversion factor, which should be multiplied by
            all distance units taken from Rhino geometry in order to convert
            them to meters.
        """
        return conversion_factor_to_meters(units)

    def _self_adj_check(self, obj_type, hb_obj, bc_ids, room_ids, bc_set, detailed):
        """Check that an adjacent object is referencing itself or its own room.

        A check will also be performed to ensure the adjacent object doesn't already
        have an adjacent pair in the model.
        """
        bc_objs = hb_obj.boundary_condition.boundary_condition_objects
        bc_obj, bc_room = bc_objs[0], bc_objs[-1]
        bc_ids.append(bc_obj)
        room_ids.append(bc_room)
        msgs = []
        # first ensure that the object is not referencing itself
        if hb_obj.identifier == bc_obj:
            msg = '{} "{}" cannot reference itself in its Surface boundary ' \
                'condition.'.format(obj_type, hb_obj.full_id)
            msg = self._validation_message_child(
                msg, hb_obj, detailed, '000201',
                error_type='Self-Referential Adjacency')
            msgs.append(msg)
        # then ensure that the object is not referencing its own room
        if hb_obj.has_parent and hb_obj.parent.has_parent:
            if hb_obj.parent.parent.identifier == bc_room:
                msg = '{} "{}" and its adjacent object "{}" cannot be a part of the ' \
                    'same Room "{}".'.format(obj_type, hb_obj.full_id, bc_obj, bc_room)
                msg = self._validation_message_child(
                    msg, hb_obj, detailed, '000202',
                    error_type='Intra-Room Adjacency')
                msgs.append(msg)
        # lastly make sure the adjacent object doesn't already have an adjacency
        if bc_obj in bc_set:
            msg = '{} "{}" is adjacent to object "{}", which has another adjacent ' \
                'object in the Model.'.format(obj_type, hb_obj.full_id, bc_obj)
            msg = self._validation_message_child(
                msg, hb_obj, detailed, '000203',
                error_type='Object with Multiple Adjacencies')
            msgs.append(msg)
        else:
            bc_set.add(bc_obj)
        return msgs if detailed else ''.join(msgs)

    def _missing_adj_msg(self, messages, hb_obj, bc_obj,
                         obj_type='Face', bc_obj_type='Face', detailed=False):
        msg = '{} "{}" has an adjacent {} that is missing from the model: ' \
            '{}'.format(obj_type, hb_obj.full_id, bc_obj_type, bc_obj)
        msg = self._validation_message_child(
            msg, hb_obj, detailed, '000204', error_type='Missing Adjacency')
        if detailed:
            messages.append([msg])
        else:
            messages.append(msg)

    @staticmethod
    def _missing_adj_check(id_checking_function, bc_ids):
        """Check whether adjacencies are missing from a model."""
        try:
            id_checking_function(bc_ids)
            return []
        except ValueError as e:
            id_pattern = re.compile('\"([^"]*)\"')
            return [obj_id for obj_id in id_pattern.findall(str(e))]

    @staticmethod
    def _adj_objects(hb_obj):
        """Check that an adjacent object is referencing itself."""
        bc_objs = hb_obj.boundary_condition.boundary_condition_objects
        return bc_objs[0], bc_objs[-1]

    def __add__(self, other):
        new_model = self.duplicate()
        new_model.add_model(other)
        return new_model

    def __iadd__(self, other):
        self.add_model(other)
        return self

    def __copy__(self):
        new_model = Model(
            self.identifier,
            [room.duplicate() for room in self._rooms],
            [face.duplicate() for face in self._orphaned_faces],
            [shade.duplicate() for shade in self._orphaned_shades],
            [aperture.duplicate() for aperture in self._orphaned_apertures],
            [door.duplicate() for door in self._orphaned_doors],
            self.units, self.tolerance, self.angle_tolerance)
        new_model._display_name = self._display_name
        new_model._user_data = None if self.user_data is None else self.user_data.copy()
        new_model._properties._duplicate_extension_attr(self._properties)
        return new_model

    def __repr__(self):
        return 'Model: %s' % self.display_name
