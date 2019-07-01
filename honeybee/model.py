# coding: utf-8
"""Honeybee Model."""
from .properties import ModelProperties
from .room import Room
from .face import Face
from .shade import Shade
from .aperture import Aperture
from .door import Door
from .boundarycondition import Outdoors, Surface
from .facetype import AirWall
from .typing import valid_string, float_in_range
import honeybee.writer as writer

from ladybug_geometry.geometry2d.pointvector import Vector2D
from ladybug_geometry.geometry3d.face import Face3D

import math


class Model(object):
    """A collection of Rooms, Faces, Shades, Apertures, and Doors representing a model.

    Properties:
        name
        name_original
        north_angle
        north_vector
        rooms
        faces
        shades
        apertures
        doors
        has_ngon_apertures
        had_ngon_doors
    """
    __slots__ = ('_name', '_name_original', '_rooms', '_faces', '_shades',
                 '_apertures', '_doors', '_room_names', '_face_names', '_shade_names',
                 '_aperture_names', '_door_names', '_properties')

    def __init__(self, name, objects, north_angle=0):
        """A collection of Rooms, Faces, Apertures, and Doors for an entire model.

        Args:
            name: Model name. Must be < 100 characters.
            objects: A list of honeybee Rooms, Faces, Apertures, and Doors.
            north_angle: An number between 0 and 360 to set the clockwise north
                direction in degrees. Default is 0.
        """
        self._name = valid_string(name, 'honeybee model name')
        self._name_original = name
        self.north_angle = north_angle

        self._rooms = []
        self._faces = []
        self._shades = []
        self._apertures = []
        self._doors = []
        self._room_names = []
        self._face_names = []
        self._shade_names = []
        self._aperture_names = []
        self._door_names = []
        for obj in objects:
            if isinstance(obj, Room):
                self.add_room(obj)
            elif isinstance(obj, Face):
                self.add_face(obj)
            elif isinstance(obj, Shade):
                self.add_shade(obj)
            elif isinstance(obj, Aperture):
                self.add_aperture(obj)
            elif isinstance(obj, Door):
                self.add_door(obj)
            else:
                raise TypeError('Expected Room, Face, Shade, Aperture or Door '
                                'for Model. Got {}'.format(type(obj)))

        self._properties = ModelProperties(self)

    @property
    def name(self):
        """The model name (including only legal characters)."""
        return self._name

    @property
    def name_original(self):
        """Original input name by user.

        If there are no illegal characters in name then name and name_original will
        be the same. Legal characters are ., A-Z, a-z, 0-9, _ and -.
        Invalid characters are automatically removed from the original name for
        compatability with simulation engines.
        """
        return self._name_original

    @property
    def north_angle(self):
        """Get or set a number between 0 and 360 for the north direction in degrees."""
        return self._north_angle

    @north_angle.setter
    def north_angle(self, value):
        self._north_angle = float_in_range(value, 0.0, 360.0, 'model north angle')
        self._north_vector = Vector2D(0, 1).rotate(math.radians(-self._north_angle))

    @property
    def north_vector(self):
        """Get or set a ladybug_geometry Vector2D for the north direction."""
        return self._north_vector

    @north_vector.setter
    def north_vector(self, value):
        assert isinstance(value, Vector2D), \
            'Expected Vector2D for north_vector. Got {}.'.format(type(value))
        self._north_vector = value
        self._north_angle = \
            math.degrees(Vector2D(0, 1).angle_clockwise(self._north_vector))

    @property
    def rooms(self):
        """A list of all Room objects in the model."""
        return self._rooms

    @property
    def faces(self):
        """A list of all Face objects in the model."""
        return self._faces

    @property
    def shades(self):
        """A list of all Shades objects in the model."""
        return self._shades

    @property
    def apertures(self):
        """A list of all Aperture objects in the model."""
        return self._apertures

    @property
    def doors(self):
        """A list of all Door objects in the model."""
        return self._doors

    @property
    def has_ngon_apertures(self):
        """Boolean noting whether the model has apertures with more than 4 sides.

        This is helpful for energy simulation since EnergyPlus cannot accept
        sub-faces with more than 4 sides. This property should be checked before
        running the triangulate_ngon_apertures() method since many models do not
        have such apertures.
        """
        for ap in self.apertures:
            if len(ap.geometry) > 4:
                return True
        return False

    @property
    def has_ngon_doors(self):
        """Boolean noting whether the model has doors with more than 4 sides.

        This is helpful for energy simulation since EnergyPlus cannot accept
        sub-faces with more than 4 sides. This property should be checked before
        running the triangulate_ngon_doors() method since many models do not have
        such doors.
        """
        for dr in self.doors:
            if len(dr.geometry) > 4:
                return True
        return False

    def get_room(self, name):
        """Get a room object in the model given the room name."""
        return self._rooms[self._room_names.index(name)]

    def get_face(self, name):
        """Get a face object in the model given the face name."""
        return self._faces[self._face_names.index(name)]

    def get_shade(self, name):
        """Get a shade object in the model given the shade name."""
        return self._shades[self._shade_names.index(name)]

    def get_aperture(self, name):
        """Get an aperture object in the model given the aperture name."""
        return self._apertures[self._aperture_names.index(name)]

    def get_door(self, name):
        """Get an door object in the model given the door name."""
        return self._doors[self._door_names.index(name)]

    def add_model(self, other_model):
        """Add another Model object to this model."""
        assert isinstance(other_model, Model), \
            'Expected Model. Got {}.'.format(type(other_model))
        for room in other_model.rooms:
            self.add_room(room)
        for face in other_model.faces:
            if not face.has_parent:
                self.add_face(face)
        for shade in other_model.shades:
            if not shade.has_parent:
                self.add_shade(shade)
        for aperture in other_model.apertures:
            if not aperture.has_parent:
                self.add_aperture(aperture)
        for door in other_model.doors:
            if not door.has_parent:
                self.add_door(door)

    def add_room(self, obj):
        """Add a Room object to the model."""
        assert isinstance(obj, Room), 'Expected Room. Got {}.'.format(type(obj))
        self._rooms.append(obj)
        self._room_names.append(obj.name)
        for face in obj.faces:
            self.add_face(face)
        for shade in obj.indoor_shades:
            self.add_shade(shade)
        for shade in obj.outdoor_shades:
            self.add_shade(shade)

    def add_face(self, obj):
        """Add a Face object to the model."""
        assert isinstance(obj, Face), 'Expected Face. Got {}.'.format(type(obj))
        self._faces.append(obj)
        self._face_names.append(obj.name)
        for ap in obj.apertures:
            self.add_aperture(ap)
        for dr in obj.doors:
            self.add_door(dr)

    def add_shade(self, obj):
        """Add an Shade object to the model."""
        assert isinstance(obj, Shade), 'Expected Shade. Got {}.'.format(type(obj))
        self._shades.append(obj)
        self._shade_names.append(obj.name)

    def add_aperture(self, obj):
        """Add an Aperture object to the model."""
        assert isinstance(obj, Aperture), 'Expected Aperture. Got {}.'.format(type(obj))
        self._apertures.append(obj)
        self._aperture_names.append(obj.name)

    def add_door(self, obj):
        """Add an Door object to the model."""
        assert isinstance(obj, Door), 'Expected Door. Got {}.'.format(type(obj))
        self._doors.append(obj)
        self._door_names.append(obj.name)

    def check_duplicate_room_names(self, raise_exception=True):
        """Check that there are no duplicate room names in the model."""
        room_count = len(self._room_names)
        unique_room_count = len(set(self._room_names))
        if room_count != unique_room_count:
            if raise_exception:
                raise ValueError('Model "{}" has {} duplicated room names.'.format(
                                 self.name_original, room_count - unique_room_count))
            return False
        return True

    def check_duplicate_face_names(self, raise_exception=True):
        """Check that there are no duplicate face names in the model."""
        face_count = len(self._face_names)
        unique_face_count = len(set(self._face_names))
        if face_count != unique_face_count:
            if raise_exception:
                raise ValueError('Model "{}" has {} duplicated face names.'.format(
                                 self.name_original, face_count - unique_face_count))
            return False
        return True

    def check_duplicate_shade_names(self, raise_exception=True):
        """Check that there are no duplicate shade names in the model."""
        shade_count = len(self._shade_names)
        unique_shade_count = len(set(self._shade_names))
        if shade_count != unique_shade_count:
            if raise_exception:
                raise ValueError('Model "{}" has {} duplicated shade names.'.format(
                                 self.name_original, shade_count - unique_shade_count))
            return False
        return True

    def check_duplicate_sub_face_names(self, raise_exception=True):
        """Check that there are no duplicate sub-face names in the model.

        Note that both apertures and doors are checked for duplicates since the two
        are counted together by EnergyPlus.
        """
        sub_face_names = self._aperture_names + self._door_names
        sf_count = len(sub_face_names)
        unique_sf_count = len(set(sub_face_names))
        if sf_count != unique_sf_count:
            if raise_exception:
                raise ValueError('Model "{}" has {} duplicated sub-face names.'.format(
                                 self.name_original, sf_count - unique_sf_count))
            return False
        return True

    def check_missing_adjacencies(self, raise_exception=True):
        """Check that all faces have adjacent objects that exist in the model."""
        for room in self.rooms:
            for face in room._faces:
                if isinstance(face.boundary_condition, Surface):
                    bc_obj_name = face.boundary_condition.boundary_condition_object
                    if bc_obj_name not in self._face_names:
                        if raise_exception:
                            raise ValueError(
                                'Face "{}" has a boundary condition object that is '
                                'missing from the model: {}.'.format(
                                    face.name_original, bc_obj_name))
                        return False
        return True

    def check_all_air_walls_adjacent(self, raise_exception=True):
        """Check that all faces with AirWall type are adjacent to other faces.

        This is a requirement for energy models.
        """
        for face in self.faces:
            if isinstance(face.type, AirWall) and not \
                    isinstance(face.boundary_condition, Surface):
                if raise_exception:
                    raise ValueError('Face "{}" is an AirWall but does not have Surface'
                                     ' boundary condition.'.format(face.name_original))
                return False
        return True

    def check_orphaned_faces(self, raise_exception=True):
        """Check that there are no faces without a parent Room in the model.

        This is a requirement for energy models.
        """
        for face in self.faces:
            if not face.has_parent:
                if raise_exception:
                    raise ValueError('Face "{}" does not have a parent '
                                     'Room.'.format(face.name_original))
                return False
        return True

    def check_orphaned_apertures(self, raise_exception=True):
        """Check that there are no orphaned apertures in the model."""
        for ap in self.apertures:
            if not ap.has_parent:
                if raise_exception:
                    raise ValueError('Aperture "{}" does not have a parent '
                                     'Face.'.format(ap.name_original))
                return False
        return True

    def check_orphaned_doors(self, raise_exception=True):
        """Check that there are no orphaned doors in the model."""
        for dr in self.doors:
            if not dr.has_parent:
                if raise_exception:
                    raise ValueError('Door "{}" does not have a parent '
                                     'Face.'.format(dr.name_original))
                return False
        return True

    def check_planar(self, tolerance, raise_exception=True):
        """Check that all of the Model's geometry components are planar.

        This includes all of the Model's Faces, Apertures, Doors and Shades.

        Args:
            tolerance: The minimum distance between a given vertex and a the
                object's's plane at which the vertex is said to lie in the plane.
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
                above the smalest size that OpenStudio will accept.
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

    def triangulate_ngon_apertures(self):
        """Triangulate all Apertures that have more than 4 sides in the model.

        This is necessary for energy simulation since EnergyPlus cannot accept
        sub-faces with more than 4 sides.
        """
        adjacent_check = [ap.name for ap in self.apertures]  # needed to check adjacency
        for i, ap in enumerate(list(self.apertures)):  # copy to avoid edit while iterate
            if len(ap.geometry) > 4 and adjacent_check[i]:
                # generate the new triangulated apertures
                ap_mesh3d = ap.triangulated_mesh3d
                new_verts = [[ap_mesh3d[v] for v in face] for face in ap_mesh3d.faces]
                new_ap_geo = [Face3D(verts, ap.geometry.plane) for verts in new_verts]
                new_aps = self._replace_aperture(ap, new_ap_geo)
                # coordinate new apertures with any adjacent apertures
                if isinstance(ap.boundary_condition, Surface):
                    adj_ap = self.get_aperture(
                        ap.boundary_condition.boundary_condition_object)
                    new_adj_ap_geo = [face.flip() for face in new_ap_geo]
                    new_adj_aps = self._replace_aperture(adj_ap, new_adj_ap_geo)
                    for new_ap, new_adj_ap in zip(new_aps, new_adj_aps):
                        new_ap.set_adjacency(new_adj_ap)
                    adj_i = adjacent_check.index(adj_ap.name)
                    adjacent_check[adj_i] = False  # ensure we don't re-triangulate

    def triangulate_ngon_doors(self):
        """Triangulate all Doors that have more than 4 sides in the model.

        This is necessary for energy simulation since EnergyPlus cannot accept
        sub-faces with more than 4 sides.
        """
        adjacent_check = [dr.name for dr in self.doors]  # needed to check adjacency
        for i, dr in enumerate(list(self.doors)):  # copy to avoid editing while iterate
            if len(dr.geometry) > 4 and adjacent_check[i]:
                # generate the new triangulated doors
                dr_mesh3d = dr.triangulated_mesh3d
                new_verts = [[dr_mesh3d[v] for v in face] for face in dr_mesh3d.faces]
                new_dr_geo = [Face3D(verts, dr.geometry.plane) for verts in new_verts]
                new_drs = self._replace_door(dr, new_dr_geo)
                # coordinate new doors with any adjacent doors
                if isinstance(dr.boundary_condition, Surface):
                    adj_dr = self.get_door(
                        dr.boundary_condition.boundary_condition_object)
                    new_adj_dr_geo = [face.flip() for face in new_dr_geo]
                    new_adj_drs = self._replace_door(adj_dr, new_adj_dr_geo)
                    for new_dr, new_adj_dr in zip(new_drs, new_adj_drs):
                        new_dr.set_adjacency(new_adj_dr)
                    adj_i = adjacent_check.index(adj_dr.name)
                    adjacent_check[adj_i] = False  # ensure we don't re-triangulate

    def _replace_aperture(self, original_ap, new_ap_geo):
        """Replace an aperture in the model with new ones built from new_ap_geo.

        Note that this method does not re-link the new apertures to new adjacent
        apertures in the model. This must be done with the returned apertures.

        Args:
            original_ap: The original Aperture object that is being replaced.
            new_ap_geo: A list of ladybug_geometry Face3D objects that will be used
                to replace the original Aperture object.

        Returns:
            new_aps: A list of the new Aperture objects that have been added to
                the model.
        """
        # make the new Apertures and add them to the model
        new_aps = []
        for i, ap_face in enumerate(new_ap_geo):
            new_ap = Aperture('{}_SubF{}'.format(original_ap.name_original, i),
                              ap_face, Outdoors())
            new_ap._properties = original_ap._properties  # transfer extension properties
            if original_ap.has_parent:
                new_ap._parent = original_ap.parent
                original_ap.parent._apertures.append(new_ap)
            self.add_aperture(new_ap)
            new_aps.append(new_ap)
        # delete the original Aperture from the model and from its parent Face
        del_i = self._aperture_names.index(original_ap.name)
        del self._apertures[del_i]
        del self._aperture_names[del_i]
        if original_ap.has_parent:
            del_i = 0
            for j, old_ap in enumerate(original_ap.parent._apertures):
                if old_ap.name == original_ap.name:
                    del_i = j
                    break
            del original_ap.parent._apertures[del_i]
        return new_aps

    def _replace_door(self, original_dr, new_dr_geo):
        """Replace a door in the model with new ones built from new_dr_geo.

        Note that this method does not re-link the new doors to new adjacent
        doors in the model. This must be done with the returned doors.

        Args:
            original_dr: The original Door object that is being replaced.
            new_dr_geo: A list of ladybug_geometry Face3D objects that will be used
                to replace the original Door object.

        Returns:
            new_drs: A list of the new Door objects that have been added to
                the model.
        """
        # make the new Doors and add them to the model
        new_drs = []
        for i, dr_face in enumerate(new_dr_geo):
            new_dr = Door('{}_SubF{}'.format(original_dr.name_original, i),
                          dr_face, Outdoors())
            new_dr._properties = original_dr._properties  # transfer extension properties
            if original_dr.has_parent:
                new_dr._parent = original_dr.parent
                original_dr.parent._doors.append(new_dr)
            self.add_door(new_dr)
            new_drs.append(new_dr)
        # delete the original Door from the model and from its parent Face
        del_i = self._door_names.index(original_dr.name)
        del self._doors[del_i]
        del self._door_names[del_i]
        if original_dr.has_parent:
            del_i = 0
            for j, old_dr in enumerate(original_dr.parent._doors):
                if old_dr.name == original_dr.name:
                    del_i = j
                    break
            del original_dr.parent._doors[del_i]
        return new_drs

    @property
    def properties(self):
        """Model properties, including Radiance, Energy and other properties."""
        return self._properties

    @property
    def to(self):
        """Model writer object.

        Use this method to access Writer class to write the model in other formats.

        Usage:
            model.to.idf(model) -> idf string.
            model.to.radiance(model) -> Radiance string.
        """
        raise NotImplementedError('Model does not yet support writing to files.')
        return writer

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'Model: %s' % self.name_original
