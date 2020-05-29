# coding: utf-8
"""Honeybee Model."""
from ._base import _Base
from .properties import ModelProperties
from .room import Room
from .face import Face
from .shade import Shade
from .aperture import Aperture
from .door import Door
from .typing import float_positive
from .boundarycondition import Surface
from .facetype import AirBoundary
import honeybee.writer.model as writer

from ladybug_geometry.geometry3d.face import Face3D


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
            checks should be performed. Default: 0.
        angle_tolerance: The max angle difference in degrees that vertices are
            allowed to differ from one another in order to consider them colinear.
            Zero indicates that no angle tolerance checks should be performed.
            Default: 0.

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
        * user_data
    """
    __slots__ = ('_rooms', '_orphaned_faces', '_orphaned_shades', '_orphaned_apertures',
                 '_orphaned_doors', '_units', '_tolerance', '_angle_tolerance')

    UNITS = ('Meters', 'Millimeters', 'Feet', 'Inches', 'Centimeters')

    def __init__(self, identifier, rooms=None, orphaned_faces=None, orphaned_shades=None,
                 orphaned_apertures=None, orphaned_doors=None,
                 units='Meters', tolerance=0, angle_tolerance=0):
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

        # import the tolerance values
        tol = 0 if 'tolerance' not in data else data['tolerance']
        angle_tol = 0 if 'angle_tolerance' not in data else data['angle_tolerance']

        # import all of the geometry
        rooms = None  # import rooms
        if 'rooms' in data and data['rooms'] is not None:
            rooms = [Room.from_dict(r, tol, angle_tol) for r in data['rooms']]
        orphaned_faces = None  # import orphaned faces
        if 'orphaned_faces' in data and data['orphaned_faces'] is not None:
            orphaned_faces = [Face.from_dict(f) for f in data['orphaned_faces']]
        orphaned_shades = None  # import orphaned shades
        if 'orphaned_shades' in data and data['orphaned_shades'] is not None:
            orphaned_shades = [Shade.from_dict(s) for s in data['orphaned_shades']]
        orphaned_apertures = None  # import orphaned apertures
        if 'orphaned_apertures' in data and data['orphaned_apertures'] is not None:
            orphaned_apertures = [Aperture.from_dict(a) for
                                  a in data['orphaned_apertures']]
        orphaned_doors = None  # import orphaned doors
        if 'orphaned_doors' in data and data['orphaned_doors'] is not None:
            orphaned_doors = [Door.from_dict(d) for d in data['orphaned_doors']]

        # import the units
        units = 'Meters' if 'units' not in data else data['units']

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
    def from_objects(cls, identifier, objects, units='Meters', tolerance=0,
                     angle_tolerance=0):
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
                checks should be performed. Default: 0.
            angle_tolerance: The max angle difference in degrees that vertices are
                allowed to differ from one another in order to consider them colinear.
                Zero indicates that no angle tolerance checks should be performed.
                Default: 0.
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
        assert value in self.UNITS, '{} is not supported as a units system. ' \
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
        self._tolerance = float_positive(value, 'model tolerance')

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
        """Add a Face object without a parent to the model."""
        assert isinstance(obj, Face), 'Expected Face. Got {}.'.format(type(obj))
        assert not obj.has_parent, 'Face "{}"" has a parent Room. Add the Room to '\
            'the model instead of the Face.'.format(obj.display_name)
        self._orphaned_faces.append(obj)

    def add_shade(self, obj):
        """Add an Shade object to the model."""
        assert isinstance(obj, Shade), 'Expected Shade. Got {}.'.format(type(obj))
        assert not obj.has_parent, 'Shade "{}"" has a parent object. Add the object to '\
            'the model instead of the Shade.'.format(obj.display_name)
        self._orphaned_shades.append(obj)

    def add_aperture(self, obj):
        """Add an Aperture object to the model."""
        assert isinstance(obj, Aperture), 'Expected Aperture. Got {}.'.format(type(obj))
        assert not obj.has_parent, 'Aperture "{}"" has a parent Face. Add the Face to '\
            'the model instead of the Aperture.'.format(obj.display_name)
        self._orphaned_apertures.append(obj)

    def add_door(self, obj):
        """Add an Door object to the model."""
        assert isinstance(obj, Door), 'Expected Door. Got {}.'.format(type(obj))
        assert not obj.has_parent, 'Door "{}"" has a parent Face. Add the Face to '\
            'the model instead of the Door.'.format(obj.display_name)
        self._orphaned_doors.append(obj)

    def get_rooms_by_identifier(self, identifiers):
        """Get a list of Room objects in the model given the Room identifiers."""
        rooms = []
        model_rooms = self._rooms
        for identifier in identifiers:
            for room in model_rooms:
                if room.identifier == identifier:
                    rooms.append(room)
                    break
            else:
                raise ValueError('Room "{}" was not found in the model.'.format(identifier))
        return rooms

    def get_faces_by_identifier(self, identifiers):
        """Get a list of Face objects in the model given the Face identifiers."""
        faces = []
        model_faces = self.faces
        for identifier in identifiers:
            for face in model_faces:
                if face.identifier == identifier:
                    faces.append(face)
                    break
            else:
                raise ValueError('Face "{}" was not found in the model.'.format(identifier))
        return faces

    def get_shades_by_identifier(self, identifiers):
        """Get a list of Shade objects in the model given the Shade identifiers."""
        shades = []
        model_shades = self.shades
        for identifier in identifiers:
            for face in model_shades:
                if face.identifier == identifier:
                    shades.append(face)
                    break
            else:
                raise ValueError('Shade "{}" was not found in the model.'.format(identifier))
        return shades

    def get_apertures_by_identifier(self, identifiers):
        """Get a list of Aperture objects in the model given the Aperture identifiers."""
        apertures = []
        model_apertures = self.apertures
        for identifier in identifiers:
            for aperture in model_apertures:
                if aperture.identifier == identifier:
                    apertures.append(aperture)
                    break
            else:
                raise ValueError(
                    'Aperture "{}" was not found in the model.'.format(identifier))
        return apertures

    def get_doors_by_identifier(self, identifiers):
        """Get a list of Door objects in the model given the Door identifiers."""
        doors = []
        model_doors = self.doors
        for identifier in identifiers:
            for door in model_doors:
                if door.identifier == identifier:
                    doors.append(door)
                    break
            else:
                raise ValueError('Door "{}" was not found in the model.'.format(identifier))
        return doors

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
            scale_fac1 = self.conversion_factor_to_meters(self.units)
            scale_fac2 = self.conversion_factor_to_meters(units)
            scale_fac = scale_fac1 / scale_fac2
            self.scale(scale_fac)
            self.tolerance = self.tolerance * scale_fac
            self.units = units

    def check_duplicate_room_identifiers(self, raise_exception=True):
        """Check that there are no duplicate Room identifiers in the model."""
        room_identifiers = set()
        duplicate_identifiers = set()
        for room in self._rooms:
            if room.identifier not in room_identifiers:
                room_identifiers.add(room.identifier)
            else:
                duplicate_identifiers.add(room.identifier)
        if len(duplicate_identifiers) != 0:
            if raise_exception:
                raise ValueError('The model has the following duplicated '
                                 'Room identifiers:\n{}'.format('\n'.join(duplicate_identifiers)))
            return False
        return True

    def check_duplicate_face_identifiers(self, raise_exception=True):
        """Check that there are no duplicate Face identifiers in the model."""
        face_identifiers = set()
        duplicate_identifiers = set()
        for face in self.faces:
            if face.identifier not in face_identifiers:
                face_identifiers.add(face.identifier)
            else:
                duplicate_identifiers.add(face.identifier)
        if len(duplicate_identifiers) != 0:
            if raise_exception:
                raise ValueError('The model has the following duplicated '
                                 'Face identifiers:\n{}'.format('\n'.join(duplicate_identifiers)))
            return False
        return True

    def check_duplicate_shade_identifiers(self, raise_exception=True):
        """Check that there are no duplicate Shade identifiers in the model."""
        shade_identifiers = set()
        duplicate_identifiers = set()
        for shade in self.shades:
            if shade.identifier not in shade_identifiers:
                shade_identifiers.add(shade.identifier)
            else:
                duplicate_identifiers.add(shade.identifier)
        if len(duplicate_identifiers) != 0:
            if raise_exception:
                raise ValueError('The model has the following duplicated '
                                 'Shade identifiers:\n{}'.format('\n'.join(duplicate_identifiers)))
            return False
        return True

    def check_duplicate_sub_face_identifiers(self, raise_exception=True):
        """Check that there are no duplicate sub-face identifiers in the model.

        Note that both Apertures and Doors are checked for duplicates since the two
        are counted together by EnergyPlus.
        """
        sub_faces = self.apertures + self.doors
        sub_face_identifiers = set()
        duplicate_identifiers = set()
        for sub_face in sub_faces:
            if sub_face.identifier not in sub_face_identifiers:
                sub_face_identifiers.add(sub_face.identifier)
            else:
                duplicate_identifiers.add(sub_face.identifier)
        if len(duplicate_identifiers) != 0:
            if raise_exception:
                raise ValueError('The model has the following duplicated sub-face '
                                 'identifiers:\n{}'.format('\n'.join(duplicate_identifiers)))
            return False
        return True

    def check_missing_adjacencies(self, raise_exception=True):
        """Check that all Faces have adjacent objects that exist in the model."""
        bc_obj_identifiers = []
        for room in self._rooms:
            for face in room._faces:
                if isinstance(face.boundary_condition, Surface):
                    bc_obj_identifiers.append(
                        face.boundary_condition.boundary_condition_object)
        try:
            self.get_faces_by_identifier(bc_obj_identifiers)
        except ValueError as e:
            if raise_exception:
                raise ValueError('A Face has an adjacent object that is missing '
                                 'from the model:\n{}'.format(e))
            return False
        return True

    def check_all_air_boundaries_adjacent(self, raise_exception=True):
        """Check that all Faces with the AirBoundary type are adjacent to other Faces.

        This is a requirement for energy simulation.
        """
        for face in self.faces:
            if isinstance(face.type, AirBoundary) and not \
                    isinstance(face.boundary_condition, Surface):
                if raise_exception:
                    raise ValueError('Face "{}" is an AirBoundary but is not adjacent '
                                     'to another Face.'.format(face.display_name))
                return False
        return True

    def check_planar(self, tolerance, raise_exception=True):
        """Check that all of the Model's geometry components are planar.

        This includes all of the Model's Faces, Apertures, Doors and Shades.

        Args:
            tolerance: The minimum distance between a given vertex and a the
                object's plane at which the vertex is said to lie in the plane.
            raise_exception: Boolean to note whether an ValueError should be
                raised if a vertex does not lie within the object's plane.
        """
        for face in self.faces:
            if not face.check_planar(tolerance, raise_exception):
                return False
        for shd in self.shades:
            if not shd.check_planar(tolerance, raise_exception):
                return False
        for ap in self.apertures:
            if not ap.check_planar(tolerance, raise_exception):
                return False
        for dr in self.doors:
            if not dr.check_planar(tolerance, raise_exception):
                return False
        return True

    def check_self_intersecting(self, raise_exception=True):
        """Check that no edges of the Model's geometry components self-intersect.

        This includes all of the Model's Faces, Apertures, Doors and Shades.

        Args:
            raise_exception: If True, a ValueError will be raised if an object
                intersects with itself (like a bowtie). Default: True.
        """
        for face in self.faces:
            if not face.check_self_intersecting(raise_exception):
                return False
        for shd in self.shades:
            if not shd.check_self_intersecting(raise_exception):
                return False
        for ap in self.apertures:
            if not ap.check_self_intersecting(raise_exception):
                return False
        for dr in self.doors:
            if not dr.check_self_intersecting(raise_exception):
                return False
        return True

    def check_non_zero(self, tolerance=0.0001, raise_exception=True):
        """Check that the Model's geometry components are above a "zero" area tolerance.

        This includes all of the Model's Faces, Apertures, Doors and Shades.

        Args:
            tolerance: The minimum acceptable area of the object. Default is 0.0001,
                which is equal to 1 cm2 when model units are meters. This is just
                above the smallest size that OpenStudio will accept.
            raise_exception: If True, a ValueError will be raised if the object
                area is below the tolerance. Default: True.
        """
        for face in self.faces:
            if not face.check_non_zero(tolerance, raise_exception):
                return False
        for shd in self.shades:
            if not shd.check_non_zero(tolerance, raise_exception):
                return False
        for ap in self.apertures:
            if not ap.check_non_zero(tolerance, raise_exception):
                return False
        for dr in self.doors:
            if not dr.check_non_zero(tolerance, raise_exception):
                return False
        return True

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

            -   parents_to_edit: An list of lists that parellels the triangulated_apertures
                in that each item represents an Aperture that has been triangulated
                in the model. However, each of these lists holds between 1 and 3 values
                for the identifiers of the original aperture and parents of the aperture.
                This information is intended to help edit parent faces that have had
                their child faces triangulated. The 3 values are as follows:

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
        for i, ap in enumerate(all_apertures):
            if len(ap.geometry) <= 4:
                pass
            elif ap.identifier not in adj_check:
                # generate the new triangulated apertures
                ap_mesh3d = ap.triangulated_mesh3d
                new_verts = [[ap_mesh3d[v] for v in face] for face in ap_mesh3d.faces]
                new_ap_geo = [Face3D(verts, ap.geometry.plane) for verts in new_verts]
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
        for i, dr in enumerate(all_doors):
            if len(dr.geometry) <= 4:
                pass
            elif dr.identifier not in adj_check:
                # generate the new triangulated doors
                dr_mesh3d = dr.triangulated_mesh3d
                new_verts = [[dr_mesh3d[v] for v in face] for face in dr_mesh3d.faces]
                new_dr_geo = [Face3D(verts, dr.geometry.plane) for verts in new_verts]
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

            -   parent_edit_info: An array of up to 3 values meant to help edit parents that
                have had their child faces triangulated. The 3 values are as follows:

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

            -   parent_edit_info: An array of up to 3 values meant to help edit parents that
                have had their child faces triangulated. The 3 values are as follows:

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

    def to_dict(self, included_prop=None, triangulate_sub_faces=False):
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
                not relevant for energy simulation. Default: False.
        """
        base = {'type': 'Model'}
        base['identifier'] = self.identifier
        base['display_name'] = self.display_name
        base['units'] = self.units
        base['properties'] = self.properties.to_dict(included_prop)
        if self._rooms != []:
            base['rooms'] = \
                [r.to_dict(True, included_prop) for r in self._rooms]
        if self._orphaned_faces != []:
            base['orphaned_faces'] = \
                [f.to_dict(True, included_prop) for f in self._orphaned_faces]
        if self._orphaned_shades != []:
            base['orphaned_shades'] = \
                [shd.to_dict(True, included_prop) for shd in self._orphaned_shades]
        if self._orphaned_apertures != []:
            base['orphaned_apertures'] = \
                [ap.to_dict(True, included_prop) for ap in self._orphaned_apertures]
        if self._orphaned_doors != []:
            base['orphaned_doors'] = \
                [dr.to_dict(True, included_prop) for dr in self._orphaned_doors]
        if self.tolerance != 0:
            base['tolerance'] = self.tolerance
        if self.angle_tolerance != 0:
            base['angle_tolerance'] = self.angle_tolerance

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

        if self.user_data is not None:
            base['user_data'] = self.user_data

        return base

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
        if units == 'Meters':
            return 1.0
        elif units == 'Millimeters':
            return 0.001
        elif units == 'Feet':
            return 0.305
        elif units == 'Inches':
            return 0.0254
        elif units == 'Centimeters':
            return 0.01
        else:
            raise ValueError(
                "You're kidding me! What units are you using?" + units + "?\n"
                "Please use Meters, Millimeters, Centimeters, Feet or Inches.")

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
        new_model._display_name = self.display_name
        new_model._user_data = None if self.user_data is None else self.user_data.copy()
        new_model._properties._duplicate_extension_attr(self._properties)
        return new_model

    def __repr__(self):
        return 'Model: %s' % self.display_name
