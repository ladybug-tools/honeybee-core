# coding: utf-8
"""Honeybee Room."""
from .properties import RoomProperties
from .face import Face
from .shade import Shade
from .facetype import get_type_from_normal, Wall, Floor
from .boundarycondition import get_bc_from_position, Outdoors, Surface
from .typing import valid_string, float_in_range
import honeybee.writer as writer

from ladybug_geometry.geometry2d.pointvector import Vector2D
from ladybug_geometry.geometry3d.pointvector import Vector3D, Point3D
from ladybug_geometry.geometry3d.plane import Plane
from ladybug_geometry.geometry3d.polyface import Polyface3D

import math


class Room(object):
    """A volume enclosed by faces, representing a single room or space.

    Properties:
        name
        name_original
        faces
        indoor_shades
        outdoor_shades
        geometry
        center
        volume
        floor_area
        exposed_area
        exterior_wall_area
        exterior_aperture_area
        average_floor_height
    """
    __slots__ = ('_name', '_name_original', '_geometry', '_faces',
                 '_indoor_shades', '_outdoor_shades', '_properties')

    def __init__(self, name, faces, tolerance=None, angle_tolerance=None):
        """A volume enclosed by faces, representing a single room or space.

        Note that, if None is input for tolerance and angle_tolerance, no checks will
        be performed to determine whether the room is a closed volume and no attempt
        will be made to flip faces in the event that they are not facing outward from
        the room volume.  As such, an input tolerance of None is intended for
        workflows where the solidity of the room volume has been evaluated elsewhere.

        Args:
            name: Room name. Must be < 100 characters.
            faces: A list or tuple of honeybee Face objects that together form the
                closed volume of a room.
            tolerance: tolerance: The maximum difference between x, y, and z values
                at which vertices of adjacent facesare considered equivalent. This is
                used in determining whether the faces form a closed volume. Default
                is None, which makes no attempt to evaluate whether the Room volume
                is closed.
            angle_tolerance: The max angle difference in degrees that vertices are
                allowed to differ from one another in order to consider them colinear.
                Default is None, which makes no attempt to evaluate whether the Room
                volume is closed.
        """
        # process the name
        self._name = valid_string(name, 'honeybee room name')
        self._name_original = name

        # process the zone volume geometry
        if not isinstance(faces, tuple):
            faces = tuple(faces)
        for face in faces:
            assert isinstance(face, Face), \
                'Expected honeybee Face. Got {}'.format(type(face))
            face._parent = self

        if tolerance is None:
            self._faces = faces
            self._geometry = None  # calculated later from faces or added by classmethods
        else:
            # try to get a closed volume between the faces
            room_polyface = Polyface3D.from_faces(
                tuple(face.geometry for face in faces), tolerance)
            if not room_polyface.is_solid and angle_tolerance is not None:
                ang_tol = math.radians(angle_tolerance)
                room_polyface = room_polyface.merge_overlapping_edges(tolerance, ang_tol)
            # replace honeybee face geometry with versions that are facing outwards
            if room_polyface.is_solid:
                for i, correct_face3d in enumerate(room_polyface.faces):
                    faces[i]._geometry = correct_face3d
            self._faces = faces
            self._geometry = room_polyface

        # initialize empty lists for room-assigned shading
        self._indoor_shades = []
        self._outdoor_shades = []

        # initialize properties for extensions
        self._properties = RoomProperties(self)

    @classmethod
    def from_polyface3d(cls, name, polyface, roof_angle=30, floor_angle=150,
                        ground_depth=0):
        """Initialize a Room from a ladybug_geometry Polyface3D object.

        Args:
            name: Room name. Must be < 100 characters.
            polyface: A ladybug_geometry Polyface3D object representing the closed
                volume of a room. The Polyface3D.is_solid property can be used to
                determine whether the polyface is a closed solid before input here.
            roof_angle: Cutting angle for roof from Z axis in degrees. Default: 30.
            floor_angle: Cutting angle for floor from Z axis in degrees. Default: 150.
            ground_depth: The Z value above which faces are considered Outdoors
                instead of Ground. Faces will have a Ground boundary condition if
                their center point lies at or below this value. Default: 0.
        """
        assert isinstance(polyface, Polyface3D), \
            'Expected ladybug_geometry Polyface3D. Got {}'.format(type(polyface))
        faces = []
        for i, face in enumerate(polyface.faces):
            faces.append(Face('{}_Face{}'.format(name, i), face,
                              get_type_from_normal(face.normal, roof_angle, floor_angle),
                              get_bc_from_position(face.boundary, ground_depth)))
        room = cls(name, faces)
        room._geometry = polyface
        return room

    @classmethod
    def from_box(cls, name, width=3.0, depth=6.0, height=3.2,
                 orientation_angle=0, origin=Point3D(0, 0, 0)):
        """Initialize a Room from parameters describing a box.

        The resulting faces of the room will always be ordered as follows:
        (Bottom, Front, Right, Back, Left, Top) where the front is facing the
        cardinal direction of the orientation_angle.

        Args:
            name: Room name. Must be < 100 characters.
            width: Number for the width of the box (in the X direction). Default: 3.0.
            depth: Number for the depth of the box (in the Y direction). Default: 6.0.
            height: Number for the height of the box (in the Z direction). Default: 3.2.
            orientation_angle: A number between 0 and 360 for the clockwise
                orientation of the box in degrees.
                (0 = North, 90 = East, 180 = South, 270 = West)
            origin: A ladybug_geometry Point3D for the origin of the room.
        """
        # create a box Polyface3D
        x_axis = Vector3D(1, 0, 0)
        if orientation_angle != 0:
            angle = -1 * math.radians(
                float_in_range(orientation_angle, 0, 360, 'orientation_angle'))
            x_axis = x_axis.rotate_xy(angle)
        base_plane = Plane(Vector3D(0, 0, 1), origin, x_axis)
        polyface = Polyface3D.from_box(width, depth, height, base_plane)

        # create the honeybee Faces
        directions = ('Bottom', 'Front', 'Right', 'Back', 'Left', 'Top')
        faces = []
        for face, dir in zip(polyface.faces, directions):
            faces.append(Face('{}_{}'.format(name, dir), face,
                              get_type_from_normal(face.normal),
                              get_bc_from_position(face.boundary)))
        room = cls(name, faces)
        room._geometry = polyface
        return room

    @property
    def name(self):
        """The room name (including only legal characters)."""
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
    def faces(self):
        """Tuple of all honeybee Faces making up this room volume."""
        return self._faces

    @property
    def indoor_shades(self):
        """Tuple of all indoor shades assigned to this room."""
        return tuple(self._indoor_shades)

    @property
    def outdoor_shades(self):
        """Tuple of all outdoor shades assigned to this room."""
        return tuple(self._outdoor_shades)

    @property
    def geometry(self):
        """A ladybug_geometry Polyface3D object representing the room."""
        if self._geometry is None:
            self._geometry = Polyface3D.from_faces(
                tuple(face.geometry for face in self._faces))
        return self._geometry

    @property
    def center(self):
        """A ladybug_geometry Point3D for the center of the room.

        Note that this is the center of the bounding box around the room geometry
        and not the volume centroid.
        """
        return self.geometry.center

    @property
    def volume(self):
        """The volume of the room.

        Note that, if this room faces do not form a closed solid (with all face normals
        pointing outward), the value of this property will not be accurate.
        """
        return self.geometry.volume

    @property
    def floor_area(self):
        """The combined area of all room floor faces."""
        return sum([face.area for face in self._faces if isinstance(face.type, Floor)])

    @property
    def exposed_area(self):
        """The combined area of all room faces with outdoor boundary conditions.

        Useful for estimating infiltration, often expressed as a flow per
        unit exposed envelope area.
        """
        return sum([face.area for face in self._faces if
                    isinstance(face.boundary_condition, Outdoors)])

    @property
    def exterior_wall_area(self):
        """The combined area of all exterior walls on the room.

        Useful for calculating glazing ratios.
        """
        wall_areas = []
        for face in self._faces:
            if isinstance(face.boundary_condition, Outdoors) and \
                    isinstance(face.type, Wall):
                wall_areas.append(face.area)
        return sum(wall_areas)

    @property
    def exterior_aperture_area(self):
        """The combined area of all exterior apertures on the room.

        Useful for calculating glazing ratios.
        """
        ap_areas = []
        for face in self._faces:
            if isinstance(face.boundary_condition, Outdoors) and len(face.apertures) > 0:
                ap_areas.extend([ap.area for ap in face._apertures])
        return sum(ap_areas)

    @property
    def average_floor_height(self):
        """The height of the room floor averaged over all floor faces in the room.

        Will be None if the room posseses no floors. Resulting value is weighted by
        the area of each of the floor faces.
        """
        heights = 0
        areas = 0
        for face in self._faces:
            if isinstance(face.type, Floor):
                heights += face.center.z * face.area
                areas += face.area
        return heights / areas if areas != 0 else None

    @property
    def has_parent(self):
        """Always False as Rooms cannot have parents."""
        return False

    def average_orientation(self, north_vector=Vector2D(0, 1)):
        """A number between 0 and 360 for the average orientation of exposed walls.

        0 = North, 90 = East, 180 = South, 270 = West.  Wil be None if the zone has
        no exterior walls. Resulting value is weighted by the area of each of the
        wall faces.

        Args:
            north_vector: A ladybug_geometry Vector2D for the north direction.
                Default is the Y-axis (0, 1).
        """
        orientations = 0
        areas = 0
        for face in self._faces:
            if isinstance(face.type, Wall) and \
                    isinstance(face.boundary_condition, Outdoors):
                orientations += face.horizontal_orientation(north_vector) * face.area
                areas += face.area
        return orientations / areas if areas != 0 else None

    def clear_shades(self):
        """Remove all indoor and outdoor shades assigned to this room."""
        self.clear_indoor_shades()
        self.clear_outdoor_shades()

    def clear_indoor_shades(self):
        """Remove all indoor shades assigned to this room."""
        for shade in self._indoor_shades:
            shade._parent = None
        self._indoor_shades = []

    def clear_outdoor_shades(self):
        """Remove all outdoor shades assigned to this room."""
        for shade in self._outdoor_shades:
            shade._parent = None
        self._outdoor_shades = []

    def add_indoor_shade(self, shade):
        """Add a Shade object to be added to the indoor of this room.

        Indoor Shade objects can be used to represent furniture, the interior
        part of light shelves, etc.
        For representing finely detailed objects like blinds or roller shades,
        it may be more apprpriate to model them as materials assigned to
        Aperture properties (like Radiance or Energy materials).

        Args:
            shade: A Shade object to add to the indoors of this room.
        """
        assert isinstance(shade, Shade), \
            'Expected Shade for indoor_shade. Got {}.'.format(type(shade))
        shade._parent = self
        self._indoor_shades.append(shade)

    def add_outdoor_shade(self, shade):
        """Add an Shade object to the outdoor of this room.

        Exterior Shade objects can be used to represent overhangs, fins, etc.
        For representing larger shade objects like trees or other buildings,
        it may be more appropriate to add them to the Model as standalone shades
        without a specific parent Room since they can shade multiple Rooms at once.

        Args:
            shade: A shade face to add to the outdoors of this room.
        """
        assert isinstance(shade, Shade), \
            'Expected Shade for outdoor_shade. Got {}.'.format(type(shade))
        shade._parent = self
        self._outdoor_shades.append(shade)

    def generate_grid(self, x_dim, y_dim=None, offset=1.0):
        """Get a list of gridded Mesh3D objects offset from the floors of this room.

        Note that the x_dim and y_dim refer to dimensions within the XY coordinate
        system of the floor faces's planes. So rotating the planes of the floor faces
        will result in rotated grid cells.

        Args:
            x_dim: The x dimension of the grid cells as a number.
            y_dim: The y dimension of the grid cells as a number. Default is None,
                which will assume the same cell dimension for y as is set for x.
            offset: A number for how far to offset the grid from the base face.
                Default is 1.0, which will not offset the grid to be 1 unit above
                the floor.

        Usage:
            room = Room.from_box(3.0, 6.0, 3.2, 180)
            floor_mesh = room.generate_mesh_grid(0.5, 0.5, 1)
            test_points = floor_mesh[0].face_centroids
        """
        floor_grids = []
        for face in self._faces:
            if isinstance(face.type, Floor):
                floor_grids.append(face.geometry.get_mesh_grid(
                    x_dim, y_dim, offset, True))
        return floor_grids

    def move(self, moving_vec):
        """Move this Room along a vector.

        Args:
            moving_vec: A ladybug_geometry Vector3D with the direction and distance
                to move the room.
        """
        for face in self._faces:
            face.move(moving_vec)
        for ishd in self._indoor_shades:
            ishd.move(moving_vec)
        for oshd in self._outdoor_shades:
            oshd.move(moving_vec)
        if self._geometry is not None:
            self._geometry = self.geometry.move(moving_vec)

    def rotate(self, axis, angle, origin):
        """Rotate this Room by a certain angle around an axis and origin.

        Args:
            axis: A ladybug_geometry Vector3D axis representing the axis of rotation.
            angle: An angle for rotation in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        for face in self._faces:
            face.rotate(axis, angle, origin)
        for ishd in self._indoor_shades:
            ishd.rotate(axis, angle, origin)
        for oshd in self._outdoor_shades:
            oshd.rotate(axis, angle, origin)
        if self._geometry is not None:
            self._geometry = self.geometry.rotate(axis, math.radians(angle), origin)

    def rotate_xy(self, angle, origin):
        """Rotate this Room counterclockwise in the world XY plane by a certain angle.

        Args:
            angle: An angle in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        for face in self._faces:
            face.rotate_xy(angle, origin)
        for ishd in self._indoor_shades:
            ishd.rotate_xy(angle, origin)
        for oshd in self._outdoor_shades:
            oshd.rotate_xy(angle, origin)
        if self._geometry is not None:
            self._geometry = self.geometry.rotate_xy(math.radians(angle), origin)

    def reflect(self, plane):
        """Reflect this Room across a plane with the input normal vector and origin.

        Args:
            plane: A ladybug_geometry Plane across which the object will
                be reflected.
        """
        assert isinstance(plane, Plane), \
            'Expected ladybug_geometry Plane. Got {}.'.format(type(plane))
        for face in self._faces:
            face.reflect(plane)
        for ishd in self._indoor_shades:
            ishd.reflect(plane)
        for oshd in self._outdoor_shades:
            oshd.reflect(plane)
        if self._geometry is not None:
            self._geometry = self.geometry.reflect(plane.n, plane.o)

    def scale(self, factor, origin=None):
        """Scale this Room by a factor from an origin point.

        Args:
            factor: A number representing how much the object should be scaled.
            origin: A ladybug_geometry Point3D representing the origin from which
                to scale. If None, it will be scaled from the World origin (0, 0, 0).
        """
        for face in self._faces:
            face.scale(factor, origin)
        for ishd in self._indoor_shades:
            ishd.scale(factor, origin)
        for oshd in self._outdoor_shades:
            oshd.scale(factor, origin)
        if self._geometry is not None:
            self._geometry = self.geometry.scale(factor, origin)

    def check_solid(self, tolerance, angle_tolerance, raise_exception=True):
        """Check whether the Room is a closed solid to within the input tolerances.

        tolerance: tolerance: The maximum difference between x, y, and z values
            at which face vertices are considered equivalent. This is used in
            determining whether the faces form a closed volume.
        angle_tolerance: The max angle difference in degrees that vertices are
            allowed to differ from one another in order to consider them colinear.
        raise_exception: Boolean to note whether a ValueError should be raised
            if the room geometry does not form a closed solid.
        """
        if self._geometry is not None and self.geometry.is_solid:
            return True
        face_geometries = tuple(face.geometry for face in self._faces)
        self._geometry = Polyface3D.from_faces(face_geometries, tolerance)
        if self.geometry.is_solid:
            return True
        ang_tol = math.radians(angle_tolerance)
        self._geometry = self.geometry.merge_overlapping_edges(tolerance, ang_tol)
        if self.geometry.is_solid:
            return True
        if raise_exception:
            raise ValueError(
                'Room "{}" is not closed to within {} tolerance and {} angle '
                'tolerance.'.format(self.name_original, tolerance, angle_tolerance))
        return False

    def check_planar(self, tolerance, raise_exception=True):
        """Check that all of the Room's geometry components are planar.

        This includes all of the Room's Faces, Apertures, Doors and Shades.

        Args:
            tolerance: The minimum distance between a given vertex and a the
                object's's plane at which the vertex is said to lie in the plane.
            raise_exception: Boolean to note whether an ValueError should be
                raised if a vertex does not lie within the object's plane.
        """
        for face in self._faces:
            if not face.check_planar(tolerance, raise_exception):
                return False
            for ap in face._apertures:
                if not ap.check_planar(tolerance, raise_exception):
                    return False
            for dr in face._doors:
                if not dr.check_planar(tolerance, raise_exception):
                    return False
        for ishd in self._indoor_shades:
            if not ishd.check_planar(tolerance, raise_exception):
                return False
        for oshd in self._outdoor_shades:
            if not oshd.check_planar(tolerance, raise_exception):
                return False
        return True

    def check_self_intersecting(self, raise_exception=True):
        """Check that no edges of the Room's geometry components self-intersect.

        This includes all of the Room's Faces, Apertures, Doors and Shades.

        Args:
            raise_exception: If True, a ValueError will be raised if an object
                intersects with itself (like a bowtie). Default: True.
        """
        for face in self._faces:
            if not face.check_self_intersecting(raise_exception):
                return False
            for ap in face._apertures:
                if not ap.check_self_intersecting(raise_exception):
                    return False
            for dr in face._doors:
                if not dr.check_self_intersecting(raise_exception):
                    return False
        for ishd in self._indoor_shades:
            if not ishd.check_self_intersecting(raise_exception):
                return False
        for oshd in self._outdoor_shades:
            if not oshd.check_self_intersecting(raise_exception):
                return False
        return True

    def check_non_zero(self, tolerance=0.0001, raise_exception=True):
        """Check that the Room's geometry components are above a "zero" area tolerance.

        This includes all of the Room's Faces, Apertures, Doors and Shades.

        Args:
            tolerance: The minimum acceptable area of the object. Default is 0.0001,
                which is equal to 1 cm2 when model units are meters. This is just
                above the smalest size that OpenStudio will accept.
            raise_exception: If True, a ValueError will be raised if the object
                area is below the tolerance. Default: True.
        """
        for face in self._faces:
            if not face.check_non_zero(tolerance, raise_exception):
                return False
            for ap in face._apertures:
                if not ap.check_non_zero(tolerance, raise_exception):
                    return False
            for dr in face._doors:
                if not dr.check_non_zero(tolerance, raise_exception):
                    return False
        for ishd in self._indoor_shades:
            if not ishd.check_non_zero(tolerance, raise_exception):
                return False
        for oshd in self._outdoor_shades:
            if not oshd.check_non_zero(tolerance, raise_exception):
                return False
        return True

    @staticmethod
    def solve_adjcency(rooms, tolerance):
        """Solve for all adjacencies between a list of input rooms.

        Args:
            rooms: A list of rooms for which adjacencies will be solved.
            tolerance: The minimum difference between the coordinate values of two
                faces at which they can be considered centered adjacent.
        """
        for i, room_1 in enumerate(rooms):
            try:
                for room_2 in rooms[i + 1:]:
                    for face_1 in room_1._faces:
                        for face_2 in room_2._faces:
                            if not isinstance(face_2.boundary_condition, Surface):
                                if face_1.geometry.is_centered_adjacent(
                                        face_2.geometry, tolerance):
                                    face_1.set_adjacency(face_2)
                                    break
            except IndexError:
                pass  # we have reached the end of the list of zones

    @property
    def properties(self):
        """Room properties, including Radiance, Energy and other properties."""
        return self._properties

    @property
    def to(self):
        """Room writer object.

        Use this method to access Writer class to write the room in other formats.

        Usage:
            room.to.idf(room) -> idf string.
            room.to.radiance(room) -> Radiance string.
        """
        raise NotImplementedError('Room does not yet support writing to files.')
        return writer

    def to_dict(self, abridged=False, included_prop=None):
        """Return Room as a dictionary.

        Args:
            abridged: Boolean to note whether the full dictionary describing the
                object should be returned (False) or just an abridged version (True).
                Default: False.
            included_prop: List of properties to filter keys that must be included in
                output dictionary. For example ['energy'] will include 'energy' key if
                available in properties to_dict. By default all the keys will be
                included. To exclude all the keys from plugins use an empty list.
        """
        base = {
            'type': self.__class__.__name__,
            'name': self.name,
            'name_original': self.name_original,
            'properties': self.properties.to_dict(abridged, included_prop)
        }
        base['faces'] = [f.to_dict(abridged, included_prop) for f in self._faces]
        if self._indoor_shades != []:
            base['indoor_shades'] = \
                [shd.to_dict(abridged, included_prop) for shd in self._indoor_shades]
        else:
            base['indoor_shades'] = None
        if self._outdoor_shades != []:
            base['outdoor_shades'] = \
                [shd.to_dict(abridged, included_prop) for shd in self._outdoor_shades]
        else:
            base['outdoor_shades'] = None
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        new_r = Room(self.name_original, tuple(face.duplicate() for face in self._faces))
        new_r._indoor_shades = [ishd.duplicate() for ishd in self._indoor_shades]
        new_r._outdoor_shades = [oshd.duplicate() for oshd in self._outdoor_shades]
        for ishd in new_r._indoor_shades:
            ishd._parent = new_r
        for oshd in new_r._outdoor_shades:
            oshd._parent = new_r
        new_r._geometry = self._geometry
        new_r._properties.duplicate_extension_attr(self._properties)
        return new_r

    def __len__(self):
        return len(self._faces)

    def __getitem__(self, key):
        return self._faces[key]

    def __iter__(self):
        return iter(self._faces)

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'Room: %s' % self.name_original
