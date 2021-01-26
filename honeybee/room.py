# coding: utf-8
"""Honeybee Room."""
from __future__ import division

from ._basewithshade import _BaseWithShade
from .typing import float_in_range, int_in_range, valid_string, clean_string
from .properties import RoomProperties
from .face import Face
from .facetype import get_type_from_normal, Wall, Floor, RoofCeiling
from .boundarycondition import get_bc_from_position, Outdoors, Ground, Surface, \
    boundary_conditions
from honeybee.orientation import angles_from_num_orient, orient_index
import honeybee.writer.room as writer

from ladybug_geometry.geometry2d.pointvector import Vector2D
from ladybug_geometry.geometry3d.pointvector import Vector3D, Point3D
from ladybug_geometry.geometry3d.ray import Ray3D
from ladybug_geometry.geometry3d.plane import Plane
from ladybug_geometry.geometry3d.mesh import Mesh3D
from ladybug_geometry.geometry3d.polyface import Polyface3D

import math


class Room(_BaseWithShade):
    """A volume enclosed by faces, representing a single room or space.

    Note that, if zero is input for tolerance and angle_tolerance, no checks
    will be performed to determine whether the room is a closed volume
    and no attempt will be made to flip faces in the event that they are not
    facing outward from the room volume.  As such, an input tolerance of 0
    is intended for workflows where the solidity of the room volume has been
    evaluated elsewhere.

    Args:
        identifier: Text string for a unique Room ID. Must be < 100 characters and
            not contain any spaces or special characters.
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
        * identifier
        * display_name
        * faces
        * multiplier
        * story
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
        * exterior_wall_aperture_area
        * exterior_skylight_aperture_area
        * average_floor_height
        * user_data
    """
    __slots__ = ('_geometry', '_faces', '_multiplier', '_story')

    def __init__(self, identifier, faces, tolerance=0, angle_tolerance=0):
        """Initialize Room."""
        _BaseWithShade.__init__(self, identifier)  # process the identifier

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
                    face = faces[i]
                    norm_init = face._geometry.normal
                    face._geometry = correct_face3d
                    if face.has_sub_faces:  # flip sub-faces to align with parent Face
                        if norm_init.angle(face._geometry.normal) > (math.pi / 2):
                            for ap in face._apertures:
                                ap._geometry = ap._geometry.flip()
                            for dr in face._doors:
                                dr._geometry = dr._geometry.flip()
            self._faces = faces
            self._geometry = room_polyface

        self._multiplier = 1  # default value that can be overridden later
        self._story = None  # default value that can be overridden later
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

        room = cls(data['identifier'], [Face.from_dict(f_dict) for f_dict in data['faces']],
                   tolerance, angle_tolerance)
        if 'display_name' in data and data['display_name'] is not None:
            room.display_name = data['display_name']
        if 'user_data' in data and data['user_data'] is not None:
            room.user_data = data['user_data']
        if 'multiplier' in data and data['multiplier'] is not None:
            room._multiplier = data['multiplier']
        if 'story' in data and data['story'] is not None:
            room._story = data['story']
        room._recover_shades_from_dict(data)

        if data['properties']['type'] == 'RoomProperties':
            room.properties._load_extension_attr_from_dict(data['properties'])
        return room

    @classmethod
    def from_polyface3d(cls, identifier, polyface, roof_angle=30, floor_angle=150,
                        ground_depth=0):
        """Initialize a Room from a ladybug_geometry Polyface3D object.

        Args:
            identifier: Text string for a unique Room ID. Must be < 100 characters and
                not contain any spaces or special characters.
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
            faces.append(Face('{}..Face{}'.format(identifier, i), face,
                              get_type_from_normal(face.normal, roof_angle, floor_angle),
                              get_bc_from_position(face.boundary, ground_depth)))
        room = cls(identifier, faces)
        room._geometry = polyface
        return room

    @classmethod
    def from_box(cls, identifier, width=3.0, depth=6.0, height=3.2,
                 orientation_angle=0, origin=Point3D(0, 0, 0)):
        """Initialize a Room from parameters describing a box.

        The resulting faces of the room will always be ordered as follows:
        (Bottom, Front, Right, Back, Left, Top) where the front is facing the
        cardinal direction of the orientation_angle.

        Args:
            identifier: Text string for a unique Room ID. Must be < 100 characters and
                not contain any spaces or special characters.
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
            faces.append(Face('{}_{}'.format(identifier, dir), face,
                              get_type_from_normal(face.normal),
                              get_bc_from_position(face.boundary)))
        room = cls(identifier, faces)
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
        This means that the "repetition" isn't in a particular direction (it's
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
    def story(self):
        """Get or set text for the story identifier to which this Room belongs.

        Rooms sharing the same story identifier are considered part of the same
        story in a Model.
        """
        return self._story

    @story.setter
    def story(self, value):
        if value is not None:
            value = valid_string(value, 'honeybee room story identifier')
        self._story = value

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
                tuple(face.geometry for face in self._faces), 0)  # use 0 tolerance
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

        Note that, if this room faces do not form a closed solid the value of this
        property will not be accurate.
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

        This is NOT the area of the wall's punched_geometry and it includes BOTH
        the area of opaque and transparent parts of the walls.
        """
        wall_areas = 0
        for f in self._faces:
            if isinstance(f.boundary_condition, Outdoors) and isinstance(f.type, Wall):
                wall_areas += f.area
        return wall_areas

    @property
    def exterior_roof_area(self):
        """Get the combined area of all exterior roofs on the room.

        This is NOT the area of the roof's punched_geometry and it includes BOTH
        the area of opaque and transparent parts of the roofs.
        """
        wall_areas = 0
        for f in self._faces:
            if isinstance(f.boundary_condition, Outdoors) and \
                    isinstance(f.type, RoofCeiling):
                wall_areas += f.area
        return wall_areas

    @property
    def exterior_aperture_area(self):
        """Get the combined area of all exterior apertures on the room."""
        ap_areas = 0
        for face in self._faces:
            if isinstance(face.boundary_condition, Outdoors) and len(face._apertures) > 0:
                ap_areas += sum(ap.area for ap in face._apertures)
        return ap_areas

    @property
    def exterior_wall_aperture_area(self):
        """Get the combined area of all apertures on exterior walls of the room."""
        ap_areas = 0
        for face in self._faces:
            if isinstance(face.boundary_condition, Outdoors) and \
                    isinstance(face.type, Wall) and len(face._apertures) > 0:
                ap_areas += sum(ap.area for ap in face._apertures)
        return ap_areas

    @property
    def exterior_skylight_aperture_area(self):
        """Get the combined area of all apertures on exterior roofs of the room."""
        ap_areas = 0
        for face in self._faces:
            if isinstance(face.boundary_condition, Outdoors) and \
                    isinstance(face.type, RoofCeiling) and len(face._apertures) > 0:
                ap_areas += sum(ap.area for ap in face._apertures)
        return ap_areas

    @property
    def average_floor_height(self):
        """Get the height of the room floor averaged over all floor faces in the room.

        The resulting value is weighted by the area of each of the floor faces.
        Will be the minimum Z value of the Room volume if the room posseses no floors.
        """
        heights = 0
        areas = 0
        for face in self._faces:
            if isinstance(face.type, Floor):
                heights += face.center.z * face.area
                areas += face.area
        return heights / areas if areas != 0 else self.geometry.min.z

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
        """Change the identifier of this object and all child objects by inserting a prefix.

        This is particularly useful in workflows where you duplicate and edit
        a starting object and then want to combine it with the original object
        into one Model (like making a model of repeated rooms) since all objects
        within a Model must have unique identifiers.

        Args:
            prefix: Text that will be inserted at the start of this object's
                (and child objects') identifier and display_name. It is recommended
                that this prefix be short to avoid maxing out the 100 allowable
                characters for honeybee identifiers.
        """
        self._identifier = clean_string('{}_{}'.format(prefix, self.identifier))
        self.display_name = '{}_{}'.format(prefix, self.display_name)
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

        Will be None if the Room has no floor faces.

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
            floor_mesh = room.generate_grid(0.5, 0.5, 1)
            test_points = floor_mesh.face_centroids
        """
        floor_grids = []
        for face in self._faces:
            if isinstance(face.type, Floor):
                floor_grids.append(face.geometry.mesh_grid(x_dim, y_dim, offset, True))
        if len(floor_grids) == 1:
            return floor_grids[0]
        elif len(floor_grids) > 1:
            return Mesh3D.join_meshes(floor_grids)
        return None

    def wall_apertures_by_ratio(self, ratio, tolerance=0.01):
        """Add apertures to all exterior walls given a ratio of aperture to face area.

        Note this method removes any existing apertures and doors on the Room's walls.
        This method attempts to generate as few apertures as necessary to meet the ratio.

        Args:
            ratio: A number between 0 and 1 (but not perfectly equal to 1)
                for the desired ratio between aperture area and face area.
            tolerance: The maximum difference between point values for them to be
                considered a part of a rectangle. This is used in the event that
                this face is concave and an attempt to subdivide the face into a
                rectangle is made. It does not affect the ability to produce apertures
                for convex Faces. Default: 0.01, suitable for objects in meters.

        Usage:

        .. code-block:: python

            room = Room.from_box(3.0, 6.0, 3.2, 180)
            room.wall_apertures_by_ratio(0.4)
        """
        for face in self._faces:
            if isinstance(face.boundary_condition, Outdoors) and \
                    isinstance(face.type, Wall):
                face.apertures_by_ratio(ratio, tolerance)

    def skylight_apertures_by_ratio(self, ratio, tolerance=0.01):
        """Add apertures to all exterior roofs given a ratio of aperture to face area.

        Note this method removes any existing apertures and overhead doors on the
        Room's roofs. This method attempts to generate as few apertures as
        necessary to meet the ratio.

        Args:
            ratio: A number between 0 and 1 (but not perfectly equal to 1)
                for the desired ratio between aperture area and face area.
            tolerance: The maximum difference between point values for them to be
                considered a part of a rectangle. This is used in the event that
                this face is concave and an attempt to subdivide the face into a
                rectangle is made. It does not affect the ability to produce apertures
                for convex Faces. Default: 0.01, suitable for objects in meters.

        Usage:

        .. code-block:: python

            room = Room.from_box(3.0, 6.0, 3.2, 180)
            room.skylight_apertures_by_ratio(0.05)
        """
        for face in self._faces:
            if isinstance(face.boundary_condition, Outdoors) and \
                    isinstance(face.type, RoofCeiling):
                face.apertures_by_ratio(ratio, tolerance)

    def ground_by_custom_surface(self, ground_geometry, tolerance=0.01,
                                 angle_tolerance=1.0):
        """Set ground boundary conditions using an array of Face3D for the ground.

        Room faces that are coplanar with the ground surface or lie completely below it
        will get a Ground boundary condition while those above will get an Outdoors
        boundary condition. Existing Faces with an indoor boundary condition will
        be unaffected.

        Args:
            ground_geometry: An array of ladybug_geometry Face3D that together
                represent the ground surface.
            tolerance: The minimum difference between the coordinate values of two
                vertices at which they can be considered equivalent. Default: 0.01,
                suitable for objects in meters.
            angle_tolerance: The max angle in degrees that the plane normals can
                differ from one another in order for them to be considered
                coplanar. (Default: 1)
        """
        # default values used throughout the check
        ang_tol = math.degrees(angle_tolerance)
        up_vec = Vector3D(0, 0, 1)

        # loop through the faces and check their relation to the ground geometry
        for face in self.faces:
            if isinstance(face.boundary_condition, (Outdoors, Ground)):
                ray = Ray3D(face.center, up_vec)
                for grnd_geo in ground_geometry:
                    # first check if the surface is below the ground surface
                    if grnd_geo.intersect_line_ray(ray):
                        face.boundary_condition = boundary_conditions.ground
                        break
                    # then check if the Face is coplanar with the ground face
                    pl1, pl2 = face.geometry.plane, grnd_geo.plane
                    if pl1.is_coplanar_tolerance(pl2, tolerance, ang_tol):
                        if grnd_geo.is_point_on_face(face.center, tolerance):
                            face.boundary_condition = boundary_conditions.ground
                            break
                else:
                    face.boundary_condition = boundary_conditions.outdoors

    def move(self, moving_vec):
        """Move this Room along a vector.

        Args:
            moving_vec: A ladybug_geometry Vector3D with the direction and distance
                to move the room.
        """
        for face in self._faces:
            face.move(moving_vec)
        self.move_shades(moving_vec)
        self.properties.move(moving_vec)
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
        self.properties.rotate(axis, angle, origin)
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
        self.properties.rotate_xy(angle, origin)
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
        self.properties.reflect(plane)
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
        self.properties.scale(factor, origin)
        if self._geometry is not None:
            self._geometry = self.geometry.scale(factor, origin)

    def remove_colinear_vertices_envelope(self, tolerance=0.01):
        """Remove colinear and duplicate vertices from this object's Faces and Sub-faces.

        Note that this does not affect any assigned Shades.

        Args:
            tolerance: The minimum distance between a vertex and the boundary segments
                at which point the vertex is considered colinear. Default: 0.01,
                suitable for objects in meters.
        """
        for face in self._faces:
            face.remove_colinear_vertices(tolerance)
            for ap in face._apertures:
                ap.remove_colinear_vertices(tolerance)
            for dr in face._doors:
                dr.remove_colinear_vertices(tolerance)
        if self._geometry is not None:
            self._geometry = Polyface3D.from_faces(
                tuple(face.geometry for face in self._faces), tolerance)

    def check_solid(self, tolerance=0.01, angle_tolerance=1, raise_exception=True):
        """Check whether the Room is a closed solid to within the input tolerances.

        Args:
            tolerance: tolerance: The maximum difference between x, y, and z values
                at which face vertices are considered equivalent. Default: 0.01,
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

    def check_sub_faces_valid(self, tolerance=0.01, angle_tolerance=1,
                              raise_exception=True):
        """Check that room's sub-faces are co-planar with faces and in the face boundary.

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
                if an sub-face is not valid.
        """
        for f in self._faces:
            if not f.check_sub_faces_valid(tolerance, angle_tolerance, raise_exception):
                return False
        return True

    def check_planar(self, tolerance=0.01, raise_exception=True):
        """Check that all of the Room's geometry components are planar.

        This includes all of the Room's Faces, Apertures, Doors and Shades.

        Args:
            tolerance: The minimum distance between a given vertex and a the
                object's plane at which the vertex is said to lie in the plane.
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
                above the smallest size that OpenStudio will accept.
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
        """Solve for adjacencies between a list of rooms.

        Note that this method will mutate the input roooms by setting Surface
        boundary conditions for any adjacent objects. However, it does NOT overwrite
        existing Surface boundary conditions and only adds new ones if faces are
        found to be adjacent with equivalent areas.

        Args:
            rooms: A list of rooms for which adjacencies will be solved.
            tolerance: The minimum difference between the coordinate values of two
                faces at which they can be considered centered adjacent. Default: 0.01,
                suitable for objects in meters.

        Returns:
            A dictionary of information about the objects that had their adjacency set.
            The dictionary has the following keys.

            -   adjacent_faces - A list of tuples with each tuple containing 2 objects
                for Faces paired in the process of solving adjacency. This data can
                be used to assign custom properties to the new adjacent Faces (like
                making all adjacencies an AirBoundary face type or assigning custom
                materials/constructions).

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

    @staticmethod
    def find_adjacency(rooms, tolerance=0.01):
        """Get a list with all adjacent pairs of Faces between input rooms.

        Note that this method does not change any boundary conditions of the input
        rooms or mutate them in any way. It's purely a geometric analysis of the
        faces between rooms.

        Args:
            rooms: A list of rooms for which adjacencies will be solved.
            tolerance: The minimum difference between the coordinate values of two
                faces at which they can be considered centered adjacent. Default: 0.01,
                suitable for objects in meters.

        Returns:
            A list of tuples with each tuple containing 2 objects for Faces that
            are adjacent to one another.
        """
        adj_faces = []  # lists of adjacencies to track
        for i, room_1 in enumerate(rooms):
            try:
                for room_2 in rooms[i + 1:]:
                    if not Polyface3D.overlapping_bounding_boxes(
                            room_1.geometry, room_2.geometry, tolerance):
                        continue  # no overlap in bounding box; adjacency impossible
                    for face_1 in room_1._faces:
                        for face_2 in room_2._faces:
                            if face_1.geometry.is_centered_adjacent(
                                    face_2.geometry, tolerance):
                                adj_faces.append((face_1, face_2))
                                break
            except IndexError:
                pass  # we have reached the end of the list of zones
        return adj_faces

    @staticmethod
    def group_by_orientation(rooms, group_count=None, north_vector=Vector2D(0, 1)):
        """Group Rooms with the same average outdoor wall orientation.

        Args:
            rooms: A list of honeybee rooms to be grouped by orientation.
            group_count: An optional positive integer to set the number of orientation
                groups to use. For example, setting this to 4 will result in rooms
                being grouped by four orientations (North, East, South, West). If None,
                the maximum number of unique groups will be used.
            north_vector: A ladybug_geometry Vector2D for the north direction.
                Default is the Y-axis (0, 1).

        Returns:
            A tuple with three items.

            -   grouped_rooms - A list of lists of honeybee rooms with each sub-list
                representing a different orientation.

            -   core_rooms - A list of honeybee rooms with no identifiable orientation.

            -   orientations - A list of numbers between 0 and 360 with one orientation
                for each branch of the output grouped_rooms. This will be a list of
                angle ranges if a value is input for group_count.
        """
        # loop through each of the rooms and get the orientation
        orient_dict = {}
        core_rooms = []
        for room in rooms:
            ori = room.average_orientation(north_vector)
            if ori is None:
                core_rooms.append(room)
            else:
                try:
                    orient_dict[ori].append(room)
                except KeyError:
                    orient_dict[ori] = []
                    orient_dict[ori].append(room)

        # sort the rooms by orientation values
        room_mtx = sorted(orient_dict.items(), key=lambda d: float(d[0]))
        orientations = [r_tup[0] for r_tup in room_mtx]
        grouped_rooms = [r_tup[1] for r_tup in room_mtx]

        # group orientations if there is an input group_count
        if group_count is not None:
            angs = angles_from_num_orient(group_count)
            p_rooms = [[] for i in range(group_count)]
            for ori, rm in zip(orientations, grouped_rooms):
                or_ind = orient_index(ori, angs)
                p_rooms[or_ind].extend(rm)
            orientations = ['{} - {}'.format(int(angs[i - 1]), int(angs[i]))
                            for i in range(group_count)]
            grouped_rooms = p_rooms
        return grouped_rooms, core_rooms, orientations

    @staticmethod
    def group_by_floor_height(rooms, min_difference=0.01):
        """Group Rooms according to their average floor height.

        Args:
            rooms: A list of honeybee rooms to be grouped by floor height.
            min_difference: An float value to denote the minimum difference
                in floor heights that is considered meaningful. This can be used
                to ensure rooms like those representing stair landings are grouped
                with those below them. Default: 0.01, which means that virtually
                any minor difference in floor heights will result in a new group.
                This assumption is suitable for models in meters.

        Returns:
            A tuple with two items.

            -   grouped_rooms - A list of lists of honeybee rooms with each sub-list
                representing a different floor height.

            -   floor_heights - A list of floor heights with one floor height for each
                sub-list of the output grouped_rooms.
        """
        # loop through each of the rooms and get the floor height
        flrhgt_dict = {}
        for room in rooms:
            flrhgt = room.average_floor_height
            try:  # assume there is already a story with the room's floor height
                flrhgt_dict[flrhgt].append(room)
            except KeyError:  # this is the first room with this floor height
                flrhgt_dict[flrhgt] = []
                flrhgt_dict[flrhgt].append(room)

        # sort the rooms by floor heights
        room_mtx = sorted(flrhgt_dict.items(), key=lambda d: float(d[0]))
        flr_hgts = [r_tup[0] for r_tup in room_mtx]
        rooms = [r_tup[1] for r_tup in room_mtx]

        # group floor heights if they differ by less than the min_difference
        floor_heights = [flr_hgts[0]]
        grouped_rooms = [rooms[0]]
        for flrh, rm in zip(flr_hgts[1:], rooms[1:]):
            if flrh - floor_heights[-1] < min_difference:
                grouped_rooms[-1].extend(rm)
            else:
                grouped_rooms.append(rm)
                floor_heights.append(flrh)
        return grouped_rooms, floor_heights

    @staticmethod
    def stories_by_floor_height(rooms, min_difference=2.0):
        """Assign story properties to a set of Rooms using their floor heights.

        Stories will be named with a standard convention ('Floor1', 'Floor2', etc.).
        Note that this method will only assign stories to Rooms that do not have
        a story identifier already assigned to them.

        Args:
            rooms: A list of rooms for which story properties will be automatically
                assigned.
            min_difference: An float value to denote the minimum difference
                in floor heights that is considered meaningful. This can be used
                to ensure rooms like those representing stair landings are grouped
                with those below them. Default: 2.0, which means that any difference
                in floor heights less than 2.0 will be considered a part of the
                same story. This assumption is suitable for models in meters.

        Returns:
            A list of the unique story names that were assigned to the input rooms.
        """
        # group the rooms by floor height
        new_rooms, _ = Room.group_by_floor_height(rooms, min_difference)

        # assign the story property to each of the groups
        story_names = []
        for i, room_list in enumerate(new_rooms):
            story_name = 'Floor{}'.format(i + 1)
            story_names.append(story_name)
            for room in room_list:
                if room.story is not None:
                    continue  # preserve any existing user-assigned story values
                room.story = story_name
        return story_names

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
                object (ie. construction sets) should be included in detail
                (False) or just referenced by identifier (True). Default: False.
            included_prop: List of properties to filter keys that must be included in
                output dictionary. For example ['energy'] will include 'energy' key if
                available in properties to_dict. By default all the keys will be
                included. To exclude all the keys from extensions use an empty list.
        """
        base = {'type': 'Room'}
        base['identifier'] = self.identifier
        base['display_name'] = self.display_name
        base['properties'] = self.properties.to_dict(abridged, included_prop)
        base['faces'] = [f.to_dict(abridged, included_prop) for f in self._faces]
        self._add_shades_to_dict(base, abridged, included_prop)
        if self.multiplier != 1:
            base['multiplier'] = self.multiplier
        if self.story is not None:
            base['story'] = self.story
        if self.user_data is not None:
            base['user_data'] = self.user_data
        return base

    def __copy__(self):
        new_r = Room(self.identifier, tuple(face.duplicate() for face in self._faces))
        new_r._display_name = self.display_name
        new_r._user_data = None if self.user_data is None else self.user_data.copy()
        new_r._multiplier = self.multiplier
        new_r._story = self.story
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
