# coding: utf-8
"""Honeybee Room."""
from ._basewithshade import _BaseWithShade
from .properties import RoomProperties
from .face import Face
from .facetype import get_type_from_normal, Wall, Floor
from .boundarycondition import get_bc_from_position, Outdoors, Surface
from .typing import float_in_range, int_in_range
import honeybee.writer.room as writer

from ladybug_geometry.geometry2d.pointvector import Vector2D
from ladybug_geometry.geometry3d.pointvector import Vector3D, Point3D
from ladybug_geometry.geometry3d.plane import Plane
from ladybug_geometry.geometry3d.polyface import Polyface3D

import math


class Room(_BaseWithShade):
    """A volume enclosed by faces, representing a single room or space.

    Args:
        name: Room name. Must be < 100 characters.
        faces: A list or tuple of honeybee Face objects that together form the
            closed volume of a room.
        tolerance: The maximum difference between x, y, and z values
            at which vertices of adjacent faces are considered equivalent. This is
            used in determining whether the faces form a closed volume. Default
            is 0, which makes no attempt to evaluate whether the Room volume
            is closed.
        angle_tolerance: The max angle difference in degrees that vertices are
            allowed to differ from one another in order to consider them colinear.
            Default is 0, which makes no attempt to evaluate whether the Room
            volume is closed.

    Properties:
        * name
        * display_name
        * faces
        * multiplier
        * indoor_furniture
        * indoor_shades
        * outdoor_shades
        * geometry
        * center
        * volume
        * floor_area
        * exposed_area
        * exterior_wall_area
        * exterior_aperture_area
        * average_floor_height
    """
    __slots__ = ('_geometry', '_faces', '_multiplier')

    def __init__(self, name, faces, tolerance=0, angle_tolerance=0):
        """A volume enclosed by faces, representing a single room or space.

        Note that, if zero is input for tolerance and angle_tolerance, no checks
        will be performed to determine whether the room is a closed volume
        and no attempt will be made to flip faces in the event that they are not
        facing outward from the room volume.  As such, an input tolerance of 0
        is intended for workflows where the solidity of the room volume has been
        evaluated elsewhere.
        """
        _BaseWithShade.__init__(self, name)  # process the name

        # process the zone volume geometry
        if not isinstance(faces, tuple):
            faces = tuple(faces)
        for face in faces:
            assert isinstance(face, Face), \
                'Expected honeybee Face. Got {}'.format(type(face))
            face._parent = self

        if tolerance == 0:
            self._faces = faces
            self._geometry = None  # calculated later from faces or added by classmethods
        else:
            # try to get a closed volume between the faces
            room_polyface = Polyface3D.from_faces(
                tuple(face.geometry for face in faces), tolerance)
            if not room_polyface.is_solid and angle_tolerance != 0:
                ang_tol = math.radians(angle_tolerance)
                room_polyface = room_polyface.merge_overlapping_edges(tolerance, ang_tol)
            # replace honeybee face geometry with versions that are facing outwards
            if room_polyface.is_solid:
                for i, correct_face3d in enumerate(room_polyface.faces):
                    faces[i]._geometry = correct_face3d
            self._faces = faces
            self._geometry = room_polyface

        self._multiplier = 1  # default value that can be overridden later
        self._properties = RoomProperties(self)  # properties for extensions

    @classmethod
    def from_dict(cls, data, tolerance=0, angle_tolerance=0):
        """Initialize an Room from a dictionary.

        Args:
            data: A dictionary representation of a Room object.
            tolerance: The maximum difference between x, y, and z values
                at which vertices of adjacent faces are considered equivalent. This is
                used in determining whether the faces form a closed volume. Default
                is 0, which makes no attempt to evaluate whether the Room volume
                is closed.
            angle_tolerance: The max angle difference in degrees that vertices are
                allowed to differ from one another in order to consider them colinear.
                Default is 0, which makes no attempt to evaluate whether the Room
                volume is closed.
        """
        # check the type of dictionary
        assert data['type'] == 'Room', 'Expected Room dictionary. ' \
            'Got {}.'.format(data['type'])

        room = cls(data['name'], [Face.from_dict(f_dict) for f_dict in data['faces']],
                   tolerance, angle_tolerance)
        if 'display_name' in data and data['display_name'] is not None:
            room._display_name = data['display_name']
        if 'multiplier' in data and data['multiplier'] is not None:
            room._multiplier = data['multiplier']
        room._recover_shades_from_dict(data)

        if data['properties']['type'] == 'RoomProperties':
            room.properties._load_extension_attr_from_dict(data['properties'])
        return room

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
                all of their vertices lie at or below this value. Default: 0.
        """
        assert isinstance(polyface, Polyface3D), \
            'Expected ladybug_geometry Polyface3D. Got {}'.format(type(polyface))
        faces = []
        for i, face in enumerate(polyface.faces):
            faces.append(Face('{}..Face{}'.format(name, i), face,
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
    def faces(self):
        """Get a tuple of all honeybee Faces making up this room volume."""
        return self._faces

    @property
    def multiplier(self):
        """Get or set an integer noting how many times this Room is repeated.

        Multipliers are used to speed up the calculation when similar Rooms are
        repeated more than once. Essentially, a given simulation with the
        Room is run once and then the result is mutliplied by the multiplier.
        This means that the "repetition" isn't in a particualr direction (it's
        essentially in the exact same location) and this comes with some
        inaccuracy. However, this error might not be too large if the Rooms
        are similar enough and it can often be worth it since it can greatly
        speed up the calculation.
        """
        return self._multiplier

    @multiplier.setter
    def multiplier(self, value):
        self._multiplier = int_in_range(value, 1, input_name='room multiplier')

    @property
    def indoor_furniture(self):
        """Array of all indoor furniture Shade objects assigned to this Room.

        Note that this property is identical to the indoor_shades property but
        it is provided here under an alternate name to make it clear that indoor
        furniture objects should be added here to the Room.
        """
        return tuple(self._indoor_shades)

    @property
    def geometry(self):
        """Get a ladybug_geometry Polyface3D object representing the room."""
        if self._geometry is None:
            self._geometry = Polyface3D.from_faces(
                tuple(face.geometry for face in self._faces))
        return self._geometry

    @property
    def center(self):
        """Get a ladybug_geometry Point3D for the center of the room.

        Note that this is the center of the bounding box around the room geometry
        and not the volume centroid.
        """
        return self.geometry.center

    @property
    def volume(self):
        """Get the volume of the room.

        Note that, if this room faces do not form a closed solid (with all face normals
        pointing outward), the value of this property will not be accurate.
        """
        return self.geometry.volume

    @property
    def floor_area(self):
        """Get the combined area of all room floor faces."""
        return sum([face.area for face in self._faces if isinstance(face.type, Floor)])

    @property
    def exposed_area(self):
        """Get the combined area of all room faces with outdoor boundary conditions.

        Useful for estimating infiltration, often expressed as a flow per
        unit exposed envelope area.
        """
        return sum([face.area for face in self._faces if
                    isinstance(face.boundary_condition, Outdoors)])

    @property
    def exterior_wall_area(self):
        """Get the combined area of all exterior walls on the room.

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
        """Get the combined area of all exterior apertures on the room.

        Useful for calculating glazing ratios.
        """
        ap_areas = []
        for face in self._faces:
            if isinstance(face.boundary_condition, Outdoors) and len(face.apertures) > 0:
                ap_areas.extend([ap.area for ap in face._apertures])
        return sum(ap_areas)

    @property
    def average_floor_height(self):
        """Get the height of the room floor averaged over all floor faces in the room.

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
        """Get a number between 0 and 360 for the average orientation of exposed walls.

        0 = North, 90 = East, 180 = South, 270 = West.  Will be None if the zone has
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

    def add_prefix(self, prefix):
        """Change the name of this object and all child objects by inserting a prefix.

        This is particularly useful in workflows where you duplicate and edit
        a starting object and then want to combine it with the original object
        into one Model (like making a model of repeated rooms) since all objects
        within a Model must have unique names.

        Args:
            prefix: Text that will be inserted at the start of this object's
                (and child objects') name and display_name. It is recommended
                that this name be short to avoid maxing out the 100 allowable
                characters for honeybee names.
        """
        self.name = '{}_{}'.format(prefix, self.display_name)
        self.properties.add_prefix(prefix)
        for face in self._faces:
            face.add_prefix(prefix)
        self._add_prefix_shades(prefix)


    def remove_indoor_furniture(self):
        """Remove all indoor furniture assigned to this Room.

        Note that this method is identical to the remove_indoor_shade method but
        it is provided here under an alternate name to make it clear that indoor
        furniture objects should be added here to the Room.
        """
        self.remove_indoor_shades()

    def add_indoor_furniture(self, shade):
        """Add a Shade object representing furniture to the Room.

        Note that this method is identical to the add_indoor_shade method but
        it is provided here under an alternate name to make it clear that indoor
        furniture objects should be added here to the Room.

        Args:
            shade: A Shade object to add to the indoors of this Room, representing
                furniture, desks, partitions, etc.
        """
        self.add_indoor_shade(shade)

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

        .. code-block:: python

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
        self.move_shades(moving_vec)
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
        self.rotate_shades(axis, angle, origin)
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
        self.rotate_xy_shades(angle, origin)
        if self._geometry is not None:
            self._geometry = self.geometry.rotate_xy(math.radians(angle), origin)

    def reflect(self, plane):
        """Reflect this Room across a plane.

        Args:
            plane: A ladybug_geometry Plane across which the object will
                be reflected.
        """
        for face in self._faces:
            face.reflect(plane)
        self.reflect_shades(plane)
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
        self.scale_shades(factor, origin)
        if self._geometry is not None:
            self._geometry = self.geometry.scale(factor, origin)

    def check_solid(self, tolerance=0.01, angle_tolerance=1, raise_exception=True):
        """Check whether the Room is a closed solid to within the input tolerances.

        Args:
            tolerance: tolerance: The maximum difference between x, y, and z values
                at which face vertices are considered equivalent. This is used in
                determining whether the faces form a closed volume. Default: 0.01,
                suitable for objects in meters.
            angle_tolerance: The max angle difference in degrees that vertices are
                allowed to differ from one another in order to consider them colinear.
                Default: 1 degree.
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
                'tolerance.'.format(self.display_name, tolerance, angle_tolerance))
        return False

    def check_planar(self, tolerance=0.01, raise_exception=True):
        """Check that all of the Room's geometry components are planar.

        This includes all of the Room's Faces, Apertures, Doors and Shades.

        Args:
            tolerance: The minimum distance between a given vertex and a the
                object's's plane at which the vertex is said to lie in the plane.
                Default: 0.01, suitable for objects in meters.
            raise_exception: Boolean to note whether an ValueError should be
                raised if a vertex does not lie within the object's plane.
        """
        for face in self._faces:
            if not face.check_planar(tolerance, raise_exception):
                return False
            for ap in face._apertures:
                if not ap.check_planar(tolerance, raise_exception):
                    return False
                if not ap._check_planar_shades(tolerance, raise_exception):
                    return False
            for dr in face._doors:
                if not dr.check_planar(tolerance, raise_exception):
                    return False
            if not face._check_planar_shades(tolerance, raise_exception):
                return False
        return self._check_planar_shades(tolerance, raise_exception)

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
                if not ap._check_self_intersecting_shades(raise_exception):
                    return False
            for dr in face._doors:
                if not dr.check_self_intersecting(raise_exception):
                    return False
            if not face._check_self_intersecting_shades(raise_exception):
                return False
        return self._check_self_intersecting_shades(raise_exception)

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
                if not ap._check_non_zero_shades(tolerance, raise_exception):
                    return False
            for dr in face._doors:
                if not dr.check_non_zero(tolerance, raise_exception):
                    return False
            if not face._check_non_zero_shades(tolerance, raise_exception):
                return False
        return self._check_non_zero_shades(tolerance, raise_exception)

    @staticmethod
    def solve_adjacency(rooms, tolerance=0.01):
        """Solve for all adjacencies between a list of input rooms.

        Args:
            rooms: A list of rooms for which adjacencies will be solved.
            tolerance: The minimum difference between the coordinate values of two
                faces at which they can be considered centered adjacent. Default: 0.01,
                suitable for objects in meters.

        Returns:
            A dictionary of adjacency information with the following keys.

            -   adjacent_faces - A list of tuples with each tuple containing 2 objects
                for Faces paired in the process of solving adjacency. This data can
                be used to assign custom properties to the new adjacent Faces (like
                making all adjacencies an AirBoundary face type or assigning custom
                materials/construcitons).

            -   adjacent_apertures - A list of tuples with each tuple containing 2
                objects for Apertures paired in the process of solving adjacency.

            -   adjacent_doors - A list of tuples with each tuple containing 2 objects
                for Doors paired in the process of solving adjacency.
        """
        # lists of adjacencies to track
        adj_info = {'adjacent_faces': [], 'adjacent_apertures': [],
                    'adjacent_doors': []}

        # solve all adjacencies between rooms
        for i, room_1 in enumerate(rooms):
            try:
                for room_2 in rooms[i + 1:]:
                    if not Polyface3D.overlapping_bounding_boxes(
                            room_1.geometry, room_2.geometry, tolerance):
                        continue  # no overlap in bounding box; adjacency impossible
                    for face_1 in room_1._faces:
                        for face_2 in room_2._faces:
                            if not isinstance(face_2.boundary_condition, Surface):
                                if face_1.geometry.is_centered_adjacent(
                                        face_2.geometry, tolerance):
                                    face_info = face_1.set_adjacency(face_2)
                                    adj_info['adjacent_faces'].append((face_1, face_2))
                                    adj_info['adjacent_apertures'].extend(
                                        face_info['adjacent_apertures'])
                                    adj_info['adjacent_doors'].extend(
                                        face_info['adjacent_doors'])
                                    break
            except IndexError:
                pass  # we have reached the end of the list of zones
        return adj_info

    @property
    def to(self):
        """Room writer object.

        Use this method to access Writer class to write the room in other formats.

        Usage:

        .. code-block:: python

            room.to.idf(room) -> idf string.
            room.to.radiance(room) -> Radiance string.
        """
        return writer

    def to_dict(self, abridged=False, included_prop=None):
        """Return Room as a dictionary.

        Args:
            abridged: Boolean to note whether the extension properties of the
                object (ie. construciton sets) should be included in detail
                (False) or just referenced by name (True). Default: False.
            included_prop: List of properties to filter keys that must be included in
                output dictionary. For example ['energy'] will include 'energy' key if
                available in properties to_dict. By default all the keys will be
                included. To exclude all the keys from extensions use an empty list.
        """
        base = {'type': 'Room'}
        base['name'] = self.name
        base['display_name'] = self.display_name
        base['properties'] = self.properties.to_dict(abridged, included_prop)
        base['faces'] = [f.to_dict(abridged, included_prop) for f in self._faces]
        self._add_shades_to_dict(base, abridged, included_prop)
        if self.multiplier != 1:
            base['multiplier'] = self.multiplier
        return base

    def __copy__(self):
        new_r = Room(self.name, tuple(face.duplicate() for face in self._faces))
        new_r._display_name = self.display_name
        new_r._multiplier = self.multiplier
        self._duplicate_child_shades(new_r)
        new_r._geometry = self._geometry
        new_r._properties._duplicate_extension_attr(self._properties)
        return new_r

    def __len__(self):
        return len(self._faces)

    def __getitem__(self, key):
        return self._faces[key]

    def __iter__(self):
        return iter(self._faces)

    def __repr__(self):
        return 'Room: %s' % self.display_name
