# coding: utf-8
"""Honeybee Room."""
from __future__ import division
import math
import uuid

from ladybug_geometry.geometry2d import Point2D, Vector2D, Polygon2D
from ladybug_geometry.geometry3d import Point3D, Vector3D, Ray3D, Plane, Face3D, \
    Mesh3D, Polyface3D
from ladybug_geometry_polyskel.polysplit import perimeter_core_subpolygons

import honeybee.writer.room as writer
from ._basewithshade import _BaseWithShade
from .typing import float_in_range, int_in_range, clean_string, \
    invalid_dict_error
from .properties import RoomProperties
from .face import Face
from .facetype import AirBoundary, Wall, Floor, RoofCeiling, get_type_from_normal
from .boundarycondition import get_bc_from_position, Outdoors, Ground, Surface, \
    boundary_conditions
from .orientation import angles_from_num_orient, orient_index
try:
    ad_bc = boundary_conditions.adiabatic
except AttributeError:  # honeybee_energy is not loaded and adiabatic does not exist
    ad_bc = None


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
        * exclude_floor_area
        * indoor_furniture
        * indoor_shades
        * outdoor_shades
        * walls
        * floors
        * roof_ceilings
        * air_boundaries
        * doors
        * apertures
        * exterior_apertures
        * geometry
        * center
        * min
        * max
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
    __slots__ = (
        '_geometry', '_faces',
        '_multiplier', '_story', '_exclude_floor_area', '_parent')

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
        self._exclude_floor_area = False  # default value that can be overridden later
        self._parent = None  # completely hidden as it is only used by Dragonfly
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
        try:
            # check the type of dictionary
            assert data['type'] == 'Room', 'Expected Room dictionary. ' \
                'Got {}.'.format(data['type'])

            # create the room object and assign properties
            faces = []
            for f_dict in data['faces']:
                try:
                    faces.append(Face.from_dict(f_dict))
                except Exception as e:
                    invalid_dict_error(f_dict, e)
            room = cls(data['identifier'], faces, tolerance, angle_tolerance)
            if 'display_name' in data and data['display_name'] is not None:
                room.display_name = data['display_name']
            if 'user_data' in data and data['user_data'] is not None:
                room.user_data = data['user_data']
            if 'multiplier' in data and data['multiplier'] is not None:
                room.multiplier = data['multiplier']
            if 'story' in data and data['story'] is not None:
                room.story = data['story']
            if 'exclude_floor_area' in data and data['exclude_floor_area'] is not None:
                room.exclude_floor_area = data['exclude_floor_area']
            room._recover_shades_from_dict(data)

            if data['properties']['type'] == 'RoomProperties':
                room.properties._load_extension_attr_from_dict(data['properties'])
            return room
        except Exception as e:
            cls._from_dict_error_message(data, e)

    @classmethod
    def from_polyface3d(cls, identifier, polyface, roof_angle=60, floor_angle=130,
                        ground_depth=0):
        """Initialize a Room from a ladybug_geometry Polyface3D object.

        Args:
            identifier: Text string for a unique Room ID. Must be < 100 characters and
                not contain any spaces or special characters.
            polyface: A ladybug_geometry Polyface3D object representing the closed
                volume of a room. The Polyface3D.is_solid property can be used to
                determine whether the polyface is a closed solid before input here.
            roof_angle: A number between 0 and 90 to set the angle from the horizontal
                plane below which faces will be considered roofs instead of
                walls. 90 indicates that all vertical faces are roofs and 0
                indicates that all horizontal faces are walls. (Default: 60,
                recommended by the ASHRAE 90.1 standard).
            floor_angle: A number between 90 and 180 to set the angle from the horizontal
                plane above which faces will be considered floors instead of
                walls. 180 indicates that all vertical faces are floors and 0
                indicates that all horizontal faces are walls. (Default: 130,
                recommended by the ASHRAE 90.1 standard).
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
        Room is run once and then the result is multiplied by the multiplier.
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
        story in a Model. Note that the story identifier has no character
        restrictions much like display_name.
        """
        return self._story

    @story.setter
    def story(self, value):
        if value is not None:
            try:
                self._story = str(value)
            except UnicodeEncodeError:  # Python 2 machine lacking the character set
                self._story = value  # keep it as unicode
        else:
            self._story = value

    @property
    def exclude_floor_area(self):
        """Get or set a boolean for whether the floor area contributes to the Model.

        Note that this will not affect the floor_area property of this Room but
        it will ensure the Room's floor area is excluded from any calculations
        when the Room is part of a Model.
        """
        return self._exclude_floor_area

    @exclude_floor_area.setter
    def exclude_floor_area(self, value):
        self._exclude_floor_area = bool(value)

    @property
    def indoor_furniture(self):
        """Array of all indoor furniture Shade objects assigned to this Room.

        Note that this property is identical to the indoor_shades property but
        it is provided here under an alternate name to make it clear that indoor
        furniture objects should be added here to the Room.
        """
        return tuple(self._indoor_shades)

    @property
    def walls(self):
        """Get a tuple of all of the Wall Faces of the Room."""
        return tuple(face for face in self._faces if isinstance(face.type, Wall))

    @property
    def floors(self):
        """Get a tuple of all of the Floor Faces of the Room."""
        return tuple(face for face in self._faces if isinstance(face.type, Floor))

    @property
    def roof_ceilings(self):
        """Get a tuple of all of the RoofCeiling Faces of the Room."""
        return tuple(face for face in self._faces if isinstance(face.type, RoofCeiling))

    @property
    def air_boundaries(self):
        """Get a tuple of all of the AirBoundary Faces of the Room."""
        return tuple(face for face in self._faces if isinstance(face.type, AirBoundary))

    @property
    def doors(self):
        """Get a tuple of all Doors of the Room."""
        drs = []
        for face in self._faces:
            if len(face._doors) > 0:
                drs.extend(face._doors)
        return tuple(drs)

    @property
    def apertures(self):
        """Get a tuple of all Apertures of the Room."""
        aps = []
        for face in self._faces:
            if len(face._apertures) > 0:
                aps.extend(face._apertures)
        return tuple(aps)

    @property
    def exterior_apertures(self):
        """Get a tuple of all exterior Apertures of the Room."""
        aps = []
        for face in self._faces:
            if isinstance(face.boundary_condition, Outdoors) and \
                    len(face._apertures) > 0:
                aps.extend(face._apertures)
        return tuple(aps)

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

        Note that this is the center of the bounding box around the room Polyface
        geometry and not the volume centroid. Also note that shades assigned to
        this room are not included in this center calculation.
        """
        return self.geometry.center

    @property
    def min(self):
        """Get a Point3D for the minimum of the bounding box around the object.

        This includes any shades assigned to this object or its children.
        """
        all_geo = self._outdoor_shades + self._indoor_shades
        all_geo.extend(self._faces)
        return self._calculate_min(all_geo)

    @property
    def max(self):
        """Get a Point3D for the maximum of the bounding box around the object.

        This includes any shades assigned to this object or its children.
        """
        all_geo = self._outdoor_shades + self._indoor_shades
        all_geo.extend(self._faces)
        return self._calculate_max(all_geo)

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
            if isinstance(face.boundary_condition, Outdoors) and \
                    len(face._apertures) > 0:
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
        Will be the minimum Z value of the Room volume if the room possesses no floors.
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
        """Change the identifier of this object and child objects by inserting a prefix.

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

    def horizontal_boundary(self, match_walls=False, tolerance=0.01):
        """Get a Face3D representing the horizontal boundary around the Room.

        This will be generated from all downward-facing Faces of the Room (essentially
        the Floor faces but can also include overhanging slanted walls). So, for
        a valid closed-volume Honeybee Room, the result should always represent
        the Room in the XY plane.

        The Z height of the resulting Face3D will be at the minimum floor height.

        Note that, if this Room is not solid, the computation of the horizontal
        boundary may fail with an exception.

        Args:
            match_walls: Boolean to note whether vertices should be inserted into
                the final Face3D that will help match the segments of the result
                back to the walls that are adjacent to the floors. If False, the
                result may lack some colinear vertices that relate the Face3D
                to the Walls, though setting this to True does not guarantee that
                all walls will relate to a segment in the result. (Default: False).
            tolerance: The minimum difference between x, y, and z coordinate values
                at which points are considered distinct. (Default: 0.01,
                suitable for objects in Meters).
        """
        # get the starting horizontal boundary
        try:
            horiz_bound = self._base_horiz_boundary(tolerance)
        except Exception as e:
            msg = 'Room "{}" is not solid and so a valid horizontal boundary for ' \
                'the Room could not be established.\n{}'.format(self.full_id, e)
            raise ValueError(msg)
        if match_walls:  # insert the wall vertices
            return self._match_walls_to_horizontal_faces([horiz_bound], tolerance)[0]
        return horiz_bound

    def horizontal_floor_boundaries(self, match_walls=False, tolerance=0.01):
        """Get a list of horizontal Face3D for the boundaries around the Room's Floors.

        Unlike the horizontal_boundary method, which uses all downward-pointing
        geometries, this method will derive horizontal boundaries using only the
        Floors. This is useful when the resulting geometry is used to specify the
        floor area in the result.

        The Z height of the resulting Face3D will be at the minimum floor height.

        Args:
            match_walls: Boolean to note whether vertices should be inserted into
                the final Face3Ds that will help match the segments of the result
                back to the walls that are adjacent to the floors. If False, the
                result may lack some colinear vertices that relate the Face3Ds
                to the Walls, though setting this to True does not guarantee that
                all walls will relate to a segment in the result. (Default: False).
            tolerance: The minimum difference between x, y, and z coordinate values
                at which points are considered distinct. (Default: 0.01,
                suitable for objects in Meters).
        """
        # gather all of the floor geometries
        flr_geo = [face.geometry for face in self.floors]

        # ensure that all geometries are horizontal with as few faces as possible
        if len(flr_geo) == 0:  # degenerate face
            return []
        elif len(flr_geo) == 1:
            if flr_geo[0].is_horizontal(tolerance):
                horiz_bound = flr_geo
            else:
                floor_height = self.geometry.min.z
                bound = [Point3D(p.x, p.y, floor_height) for p in flr_geo[0].boundary]
                holes = None
                if flr_geo[0].has_holes:
                    holes = [[Point3D(p.x, p.y, floor_height) for p in hole]
                             for hole in flr_geo[0].holes]
                horiz_bound = [Face3D(bound, holes=holes)]
        else:  # multiple geometries to be joined together
            floor_height = self.geometry.min.z
            horiz_geo = []
            for fg in flr_geo:
                if fg.is_horizontal(tolerance) and \
                        abs(floor_height - fg.min.z) <= tolerance:
                    horiz_geo.append(fg)
                else:  # project the face geometry into the XY plane
                    bound = [Point3D(p.x, p.y, floor_height) for p in fg.boundary]
                    holes = None
                    if fg.has_holes:
                        holes = [[Point3D(p.x, p.y, floor_height) for p in hole]
                                 for hole in fg.holes]
                    horiz_geo.append(Face3D(bound, holes=holes))
            # join the coplanar horizontal faces together
            horiz_bound = Face3D.join_coplanar_faces(horiz_geo, tolerance)

        if match_walls:  # insert the wall vertices
            return self._match_walls_to_horizontal_faces(horiz_bound, tolerance)
        return horiz_bound

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
        """Get a gridded Mesh3D objects offset from the floors of this room.

        Note that the x_dim and y_dim refer to dimensions within the XY coordinate
        system of the floor faces's planes. So rotating the planes of the floor faces
        will result in rotated grid cells.

        Will be None if the Room has no floor faces.

        Args:
            x_dim: The x dimension of the grid cells as a number.
            y_dim: The y dimension of the grid cells as a number. Default is None,
                which will assume the same cell dimension for y as is set for x.
            offset: A number for how far to offset the grid from the base face.
                Default is 1.0, which will offset the grid to be 1 unit above
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
                try:
                    floor_grids.append(
                        face.geometry.mesh_grid(x_dim, y_dim, offset, True))
                except AssertionError:  # grid tolerance not fine enough
                    pass
        if len(floor_grids) == 1:
            return floor_grids[0]
        elif len(floor_grids) > 1:
            return Mesh3D.join_meshes(floor_grids)
        return None

    def generate_exterior_face_grid(
            self, dimension, offset=0.1, face_type='Wall', punched_geometry=False):
        """Get a gridded Mesh3D offset from the exterior Faces of this Room.

        This will be None if the Room has no exterior Faces.

        Args:
            dimension: The dimension of the grid cells as a number.
            offset: A number for how far to offset the grid from the base face.
                Positive numbers indicate an offset towards the exterior. (Default
                is 0.1, which will offset the grid to be 0.1 unit from the faces).
            face_type: Text to specify the type of face that will be used to
                generate grids. Note that only Faces with Outdoors boundary
                conditions will be used, meaning that most Floors will typically
                be excluded unless they represent the underside of a cantilever.
                Choose from the following. (Default: Wall).

                * Wall
                * Roof
                * Floor
                * All

            punched_geometry: Boolean to note whether the punched_geometry of the faces
                should be used (True) with the areas of sub-faces removed from the grid
                or the full geometry should be used (False). (Default:False).

        Usage:

        .. code-block:: python

            room = Room.from_box(3.0, 6.0, 3.2, 180)
            face_mesh = room.generate_exterior_face_grid(0.5)
            test_points = face_mesh.face_centroids
        """
        # select the correct face type based on the input
        face_t = face_type.title()
        if face_t == 'Wall':
            ft = Wall
        elif face_t in ('Roof', 'Roofceiling'):
            ft = RoofCeiling
        elif face_t == 'All':
            ft = (Wall, RoofCeiling, Floor)
        elif face_t == 'Floor':
            ft = Floor
        else:
            raise ValueError('Unrecognized face_type "{}".'.format(face_type))
        face_attr = 'punched_geometry' if punched_geometry else 'geometry'
        # loop through the faces and generate grids
        face_grids = []
        for face in self._faces:
            if isinstance(face.type, ft) and \
                    isinstance(face.boundary_condition, Outdoors):
                try:
                    f_geo = getattr(face, face_attr)
                    face_grids.append(
                        f_geo.mesh_grid(dimension, None, offset, False))
                except AssertionError:  # grid tolerance not fine enough
                    pass
        # join the grids together if there are several ones
        if len(face_grids) == 1:
            return face_grids[0]
        elif len(face_grids) > 1:
            return Mesh3D.join_meshes(face_grids)
        return None

    def generate_exterior_aperture_grid(
            self, dimension, offset=0.1, aperture_type='All'):
        """Get a gridded Mesh3D offset from the exterior Apertures of this room.

        Will be None if the Room has no exterior Apertures.

        Args:
            dimension: The dimension of the grid cells as a number.
            offset: A number for how far to offset the grid from the base aperture.
                Positive numbers indicate an offset towards the exterior while
                negative numbers indicate an offset towards the interior, essentially
                modeling the value of sun on the building interior. (Default
                is 0.1, which will offset the grid to be 0.1 unit from the apertures).
            aperture_type: Text to specify the type of Aperture that will be used to
                generate grids. Window indicates Apertures in Walls. Choose from
                the following. (Default: All).

                * Window
                * Skylight
                * All

        Usage:

        .. code-block:: python

            room = Room.from_box(3.0, 6.0, 3.2, 180)
            room[3].apertures_by_ratio(0.4)
            aperture_mesh = room.generate_exterior_aperture_grid(0.5)
            test_points = aperture_mesh.face_centroids
        """
        # select the correct face type based on the input
        ap_t = aperture_type.title()
        if ap_t == 'Window':
            ft = Wall
        elif ap_t == 'Skylight':
            ft = RoofCeiling
        elif ap_t == 'All':
            ft = (Wall, RoofCeiling, Floor)
        else:
            raise ValueError('Unrecognized aperture_type "{}".'.format(aperture_type))
        # loop through the faces and generate grids
        ap_grids = []
        for face in self._faces:
            if isinstance(face.type, ft) and \
                    isinstance(face.boundary_condition, Outdoors):
                for ap in face.apertures:
                    try:
                        ap_grids.append(
                            ap.geometry.mesh_grid(dimension, None, offset, False))
                    except AssertionError:  # grid tolerance not fine enough
                        pass
        # join the grids together if there are several ones
        if len(ap_grids) == 1:
            return ap_grids[0]
        elif len(ap_grids) > 1:
            return Mesh3D.join_meshes(ap_grids)
        return None

    def wall_apertures_by_ratio(self, ratio, tolerance=0.01):
        """Add apertures to all exterior walls given a ratio of aperture to face area.

        Note this method removes any existing apertures and doors on the Room's walls.
        This method attempts to generate as few apertures as necessary to meet the ratio.

        Args:
            ratio: A number between 0 and 1 (but not perfectly equal to 1)
                for the desired ratio between aperture area and face area.
            tolerance: The maximum difference between point values for them to be
                considered equivalent. (Default: 0.01, suitable for objects in meters).

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
                considered equivalent. (Default: 0.01, suitable for objects in meters).

        Usage:

        .. code-block:: python

            room = Room.from_box(3.0, 6.0, 3.2, 180)
            room.skylight_apertures_by_ratio(0.05)
        """
        for face in self._faces:
            if isinstance(face.boundary_condition, Outdoors) and \
                    isinstance(face.type, RoofCeiling):
                face.apertures_by_ratio(ratio, tolerance)

    def simplify_apertures(self, tolerance=0.01):
        """Convert all Apertures on this Room to be a simple window ratio.

        This is useful for studies where faster simulation times are desired and
        the window ratio is the critical factor driving the results (as opposed
        to the detailed geometry of the window). Apertures assigned to concave
        Faces will not be simplified given that the apertures_by_ratio method
        likely won't improve the cleanliness of the apertures for such cases.

        Args:
            tolerance: The maximum difference between point values for them to be
                considered equivalent. (Default: 0.01, suitable for objects in meters).
        """
        for face in self.faces:
            f_ap = face._apertures
            if len(f_ap) != 0 and face.geometry.is_convex:
                # reset boundary conditions to outdoors so new apertures can be added
                if not isinstance(face.boundary_condition, Outdoors):
                    face.boundary_condition = boundary_conditions.outdoors
                face.apertures_by_ratio(face.aperture_ratio, tolerance)

    def rectangularize_apertures(
            self, subdivision_distance=None, max_separation=None, merge_all=False,
            tolerance=0.01, angle_tolerance=1.0):
        """Convert all Apertures on this Room to be rectangular.

        This is useful when exporting to simulation engines that only accept
        rectangular window geometry. This method will always result ing Rooms where
        all Apertures are rectangular. However, if the subdivision_distance is not
        set, some Apertures may extend past the parent Face or may collide with
        one another.

        Args:
            subdivision_distance: A number for the resolution at which the
                non-rectangular Apertures will be subdivided into smaller
                rectangular units. Specifying a number here ensures that the
                resulting rectangular Apertures do not extend past the parent
                Face or collide with one another. If None, all non-rectangular
                Apertures will be rectangularized by taking the bounding rectangle
                around the Aperture. (Default: None).
            max_separation: A number for the maximum distance between non-rectangular
                Apertures at which point the Apertures will be merged into a single
                rectangular geometry. This is often helpful when there are several
                triangular Apertures that together make a rectangle when they are
                merged across their frames. In such cases, this max_separation
                should be set to a value that is slightly larger than the window frame.
                If None, no merging of Apertures will happen before they are
                converted to rectangles. (Default: None).
            merge_all: Boolean to note whether all apertures should be merged before
                they are rectangularized. If False, only non-rectangular apertures
                will be merged before rectangularization. Note that this argument
                has no effect when the max_separation is None. (Default: False).
            tolerance: The maximum difference between point values for them to be
                considered equivalent. (Default: 0.01, suitable for objects in meters).
            angle_tolerance: The max angle in degrees that the corners of the
                rectangle can differ from a right angle before it is not
                considered a rectangle. (Default: 1).
        """
        for face in self._faces:
            face.rectangularize_apertures(
                subdivision_distance, max_separation, merge_all,
                tolerance, angle_tolerance
            )

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
                vertices at which they can be considered equivalent. (Default: 0.01,
                suitable for objects in meters).
            angle_tolerance: The max angle in degrees that the plane normals can
                differ from one another in order for them to be considered
                coplanar. (Default: 1).
        """
        select_faces = self.faces_by_guide_surface(
            ground_geometry, Vector3D(0, 0, -1), tolerance, angle_tolerance)
        for face in select_faces:
            if face.can_be_ground and \
                    isinstance(face.boundary_condition, (Outdoors, Ground)):
                face.boundary_condition = boundary_conditions.ground

    def faces_by_guide_surface(self, surface_geometry, directional_vector=None,
                               tolerance=0.01, angle_tolerance=1.0):
        """Get the Faces of the Room that are touching and coplanar with a given surface.

        This is useful in workflows were one would like to set the properties
        of a group of Faces using a guide surface, like setting a series of faces
        along a given stretch of a parti wall to be adiabatic.

        Args:
            surface_geometry: An array of ladybug_geometry Face3D that together
                represent the guide surface.
            directional_vector: An optional Vector3D to select the room Faces that
                lie on a certain side of the surface_geometry. For example, using
                (0, 0, -1) will include all Faces that lie below the surface_geometry
                in the resulting selection.
            tolerance: The minimum difference between the coordinate values of two
                vertices at which they can be considered equivalent. (Default: 0.01,
                suitable for objects in meters).
            angle_tolerance: The max angle in degrees that the plane normals can
                differ from one another in order for them to be considered
                coplanar. (Default: 1).
        """
        selected_faces, ang_tol = [], math.radians(angle_tolerance)
        if directional_vector is None:  # only check for co-planarity
            for face in self.faces:
                for srf_geo in surface_geometry:
                    pl1, pl2 = face.geometry.plane, srf_geo.plane
                    if pl1.is_coplanar_tolerance(pl2, tolerance, ang_tol):
                        pt_on_face = face.geometry._point_on_face(tolerance * 2)
                        if srf_geo.is_point_on_face(pt_on_face, tolerance):
                            selected_faces.append(face)
                            break
        else:  # first check to see if the Face is on the correct side of the surface
            rev_vector = directional_vector.reverse()
            for face in self.faces:
                ray = Ray3D(face.center, rev_vector)
                for srf_geo in surface_geometry:
                    if srf_geo.intersect_line_ray(ray):
                        selected_faces.append(face)
                        break
                    pl1, pl2 = face.geometry.plane, srf_geo.plane
                    if pl1.is_coplanar_tolerance(pl2, tolerance, ang_tol):
                        pt_on_face = face.geometry._point_on_face(tolerance * 2)
                        if srf_geo.is_point_on_face(pt_on_face, tolerance):
                            selected_faces.append(face)
                            break
        return selected_faces

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

    def remove_colinear_vertices_envelope(self, tolerance=0.01, delete_degenerate=False):
        """Remove colinear and duplicate vertices from this object's Faces and Sub-faces.

        If degenerate geometry is found in the process of removing colinear vertices,
        an exception will be raised. Note that this does not affect the assigned Shades.

        Args:
            tolerance: The minimum distance between a vertex and the boundary segments
                at which point the vertex is considered colinear. Default: 0.01,
                suitable for objects in meters.
            delete_degenerate: Boolean to note whether degenerate Faces, Apertures and
                Doors (objects that evaluate to less than 3 vertices at the tolerance)
                should be deleted from the Room instead of raising a ValueError.
                (Default: False).
        """
        if delete_degenerate:
            new_faces, i_to_remove = list(self._faces), []
            for i, face in enumerate(new_faces):
                try:
                    face.remove_colinear_vertices(tolerance)
                    face.remove_degenerate_sub_faces(tolerance)
                except ValueError:  # degenerate face found!
                    i_to_remove.append(i)
            for i in reversed(i_to_remove):
                new_faces.pop(i)
            self._faces = tuple(new_faces)
        else:
            try:
                for face in self._faces:
                    face.remove_colinear_vertices(tolerance)
                    for ap in face._apertures:
                        ap.remove_colinear_vertices(tolerance)
                    for dr in face._doors:
                        dr.remove_colinear_vertices(tolerance)
            except ValueError as e:
                raise ValueError(
                    'Room "{}" contains invalid geometry.\n  {}'.format(
                        self.full_id, str(e).replace('\n', '\n  ')))
        if self._geometry is not None:
            self._geometry = Polyface3D.from_faces(
                tuple(face.geometry for face in self._faces), tolerance)

    def clean_envelope(self, adjacency_dict, tolerance=0.01):
        """Remove colinear and duplicate vertices from this object's Faces and Sub-faces.

        This method also automatically removes degenerate Faces and coordinates
        adjacent Faces with the adjacency_dict to ensure matching numbers of
        vertices, which is a requirement for engines like EnergyPlus.

        Args:
            adjacency_dict: A dictionary containing the identifiers of Room Faces as
                keys and Honeybee Face objects as values. This is used to indicate the
                target number of vertices that each Face should have after colinear
                vertices are removed. This can be used to ensure adjacent Faces
                have matching numbers of vertices, which is a requirement for
                certain interfaces like EnergyPlus.
            tolerance: The minimum distance between a vertex and the boundary segments
                at which point the vertex is considered colinear. Default: 0.01,
                suitable for objects in meters.

        Returns:
            A dictionary containing the identifiers of adjacent Faces as keys and
            Honeybee Face objects as values. This can be used as an input in future
            Rooms on which this method is run to ensure adjacent Faces have matching
            numbers of vertices, which is a requirement for certain interfaces
            like EnergyPlus.
        """
        adj_dict = {}
        new_faces, i_to_remove = list(self._faces), []
        for i, face in enumerate(new_faces):
            try:  # first make sure that the geometry is not degenerate
                new_geo = face.geometry.remove_colinear_vertices(tolerance)
            except AssertionError:  # degenerate face found!
                i_to_remove.append(i)
                continue
            # see if the geometry matches its adjacent geometry
            if isinstance(face.boundary_condition, Surface):
                try:
                    adj_face = adjacency_dict[face.identifier]
                    if len(new_geo) != len(adj_face.geometry):
                        new_geo = adj_face.geometry.flip()
                except KeyError:  # the adjacent object has not been found yet
                    pass
                adj_dict[face.boundary_condition.boundary_condition_object] = face
            # update geometry and remove degenerate Apertures and Doors
            face._geometry = new_geo
            face._punched_geometry = None  # reset so that it can be re-computed
            face.remove_degenerate_sub_faces(tolerance)
        # remove any degenerate Faces from the Room
        for i in reversed(i_to_remove):
            new_faces.pop(i)
        self._faces = tuple(new_faces)
        if self._geometry is not None:
            self._geometry = Polyface3D.from_faces(
                tuple(face.geometry for face in self._faces), tolerance)
        return adj_dict

    def is_geo_equivalent(self, room, tolerance=0.01):
        """Get a boolean for whether this object is geometrically equivalent to another.

        This will also check all child Faces, Apertures, Doors and Shades
        for equivalency.

        Args:
            room: Another Room for which geometric equivalency will be tested.
            tolerance: The minimum difference between the coordinate values of two
                vertices at which they can be considered geometrically equivalent.

        Returns:
            True if geometrically equivalent. False if not geometrically equivalent.
        """
        met_1 = (self.display_name, self.multiplier, self.story, self.exclude_floor_area)
        met_2 = (room.display_name, room.multiplier, room.story, room.exclude_floor_area)
        if met_1 != met_2:
            return False
        if len(self._faces) != len(room._faces):
            return False
        for f1, f2 in zip(self._faces, room._faces):
            if not f1.is_geo_equivalent(f2, tolerance):
                return False
        if not self._are_shades_equivalent(room, tolerance):
            return False
        return True

    def check_solid(self, tolerance=0.01, angle_tolerance=1, raise_exception=True,
                    detailed=False):
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
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        if self._geometry is not None and self.geometry.is_solid:
            return [] if detailed else ''
        face_geometries = tuple(face.geometry for face in self._faces)
        self._geometry = Polyface3D.from_faces(face_geometries, tolerance)
        if self.geometry.is_solid:
            return [] if detailed else ''
        ang_tol = math.radians(angle_tolerance)
        self._geometry = self.geometry.merge_overlapping_edges(tolerance, ang_tol)
        if self.geometry.is_solid:
            return [] if detailed else ''
        msg = 'Room "{}" is not closed to within {} tolerance and {} angle ' \
            'tolerance.\n  {} naked edges found\n  {} non-manifold edges found'.format(
                self.full_id, tolerance, angle_tolerance,
                len(self._geometry.naked_edges), len(self._geometry.non_manifold_edges))
        full_msg = self._validation_message(
            msg, raise_exception, detailed, '000106',
            error_type='Non-Solid Room Geometry')
        if detailed:  # add the naked and non-manifold edges to helper_geometry
            help_edges = [ln.to_dict() for ln in self.geometry.naked_edges]
            help_edges.extend([ln.to_dict() for ln in self.geometry.non_manifold_edges])
            full_msg[0]['helper_geometry'] = help_edges
        return full_msg

    def check_sub_faces_valid(self, tolerance=0.01, angle_tolerance=1,
                              raise_exception=True, detailed=False):
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
                if an sub-face is not valid. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        detailed = False if raise_exception else detailed
        msgs = []
        for f in self._faces:
            msg = f.check_sub_faces_valid(tolerance, angle_tolerance, False, detailed)
            if detailed:
                msgs.extend(msg)
            elif msg != '':
                msgs.append(msg)
        if len(msgs) == 0:
            return [] if detailed else ''
        elif detailed:
            return msgs
        full_msg = 'Room "{}" contains invalid sub-faces (Apertures and Doors).' \
            '\n  {}'.format(self.full_id, '\n  '.join(msgs))
        if raise_exception and len(msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def check_sub_faces_overlapping(
            self, tolerance=0.01, raise_exception=True, detailed=False):
        """Check that this Room's sub-faces do not overlap with one another.

        Args:
            tolerance: The minimum distance that two sub-faces must overlap in order
                for them to be considered overlapping and invalid. (Default: 0.01,
                suitable for objects in meters).
            raise_exception: Boolean to note whether a ValueError should be raised
                if a sub-faces overlap with one another. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        detailed = False if raise_exception else detailed
        msgs = []
        for f in self._faces:
            msg = f.check_sub_faces_overlapping(tolerance, False, detailed)
            if detailed:
                msgs.extend(msg)
            elif msg != '':
                msgs.append(msg)
        if len(msgs) == 0:
            return [] if detailed else ''
        elif detailed:
            return msgs
        full_msg = 'Room "{}" contains overlapping sub-faces.' \
            '\n  {}'.format(self.full_id, '\n  '.join(msgs))
        if raise_exception and len(msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def check_upside_down_faces(
            self, angle_tolerance=1, raise_exception=True, detailed=False):
        """Check whether the Room's Faces have the correct direction for the face type.

        This method will only report Floors that are pointing upwards or RoofCeilings
        that are pointed downwards. These cases are likely modeling errors and are in
        danger of having their vertices flipped by EnergyPlus, causing them to
        not see the sun.

        Args:
            angle_tolerance: The max angle in degrees that the Face normal can
                differ from up or down before it is considered a case of a downward
                pointing RoofCeiling or upward pointing Floor. Default: 1 degree.
            raise_exception: Boolean to note whether an ValueError should be
                raised if the Face is an an upward pointing Floor or a downward
                pointing RoofCeiling.
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        detailed = False if raise_exception else detailed
        msgs = []
        for f in self._faces:
            msg = f.check_upside_down(angle_tolerance, False, detailed)
            if detailed:
                msgs.extend(msg)
            elif msg != '':
                msgs.append(msg)
        if len(msgs) == 0:
            return [] if detailed else ''
        elif detailed:
            return msgs
        full_msg = 'Room "{}" contains upside down Faces.' \
            '\n  {}'.format(self.full_id, '\n  '.join(msgs))
        if raise_exception and len(msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def check_planar(self, tolerance=0.01, raise_exception=True, detailed=False):
        """Check that all of the Room's geometry components are planar.

        This includes all of the Room's Faces, Apertures, Doors and Shades.

        Args:
            tolerance: The minimum distance between a given vertex and a the
                object's plane at which the vertex is said to lie in the plane.
                Default: 0.01, suitable for objects in meters.
            raise_exception: Boolean to note whether an ValueError should be
                raised if a vertex does not lie within the object's plane.
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        detailed = False if raise_exception else detailed
        msgs = [self._check_planar_shades(tolerance, detailed)]
        for face in self._faces:
            msgs.append(face.check_planar(tolerance, False, detailed))
            msgs.append(face._check_planar_shades(tolerance, detailed))
            for ap in face._apertures:
                msgs.append(ap.check_planar(tolerance, False, detailed))
                msgs.append(ap._check_planar_shades(tolerance, detailed))
            for dr in face._doors:
                msgs.append(dr.check_planar(tolerance, False, detailed))
                msgs.append(dr._check_planar_shades(tolerance, detailed))
        full_msgs = [msg for msg in msgs if msg]
        if len(full_msgs) == 0:
            return [] if detailed else ''
        elif detailed:
            return [m for megs in full_msgs for m in megs]
        full_msg = 'Room "{}" contains non-planar geometry.' \
            '\n  {}'.format(self.full_id, '\n  '.join(full_msgs))
        if raise_exception and len(full_msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def check_self_intersecting(self, tolerance=0.01, raise_exception=True,
                                detailed=False):
        """Check that no edges of the Room's geometry components self-intersect.

        This includes all of the Room's Faces, Apertures, Doors and Shades.

        Args:
            tolerance: The minimum difference between the coordinate values of two
                vertices at which they can be considered equivalent. Default: 0.01,
                suitable for objects in meters.
            raise_exception: If True, a ValueError will be raised if an object
                intersects with itself (like a bow tie). (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        detailed = False if raise_exception else detailed
        msgs = [self._check_self_intersecting_shades(tolerance, detailed)]
        for face in self._faces:
            msgs.append(face.check_self_intersecting(tolerance, False, detailed))
            msgs.append(face._check_self_intersecting_shades(tolerance, detailed))
            for ap in face._apertures:
                msgs.append(ap.check_self_intersecting(tolerance, False, detailed))
                msgs.append(ap._check_self_intersecting_shades(tolerance, detailed))
            for dr in face._doors:
                msgs.append(dr.check_self_intersecting(tolerance, False, detailed))
                msgs.append(dr._check_self_intersecting_shades(tolerance, detailed))
        full_msgs = [msg for msg in msgs if msg]
        if len(full_msgs) == 0:
            return [] if detailed else ''
        elif detailed:
            return [m for megs in full_msgs for m in megs]
        full_msg = 'Room "{}" contains self-intersecting geometry.' \
            '\n  {}'.format(self.full_id, '\n  '.join(full_msgs))
        if raise_exception and len(full_msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def check_degenerate(self, tolerance=0.01, raise_exception=True, detailed=False):
        """Check whether the Room is degenerate with zero volume.

        Args:
            tolerance: tolerance: The maximum difference between x, y, and z values
                at which face vertices are considered equivalent. (Default: 0.01,
                suitable for objects in meters).
            raise_exception: Boolean to note whether a ValueError should be raised
                if the room geometry is degenerate. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        if len(self._faces) >= 4 and self.volume > tolerance:
            return [] if detailed else ''
        msg = 'Room "{}" is degenerate with zero volume. It should be deleted'.format(
                self.full_id)
        return self._validation_message(
            msg, raise_exception, detailed, '000107',
            error_type='Degenerate Room Volume')

    def merge_coplanar_faces(
            self, tolerance=0.01, angle_tolerance=1, orthogonal_only=False):
        """Merge coplanar Faces of this Room.

        This is often useful before running Room.intersect_adjacency between
        multiple Rooms as it will ensure the result is clean with any previous
        intersections erased.

        This method attempts to preserve as many properties as possible for the
        split Faces but, when Faces are merged, the properties of one of the
        merged faces will determine the face type and boundary condition. Also, all
        Face extension attributes will be removed (reset to default) and, if merged
        Faces originally had Surface boundary conditions, they will be reset
        to Outdoors.

        Args:
            tolerance: The minimum difference between the coordinate values of two
                faces at which they can be considered adjacent. Default: 0.01,
                suitable for objects in meters.
            angle_tolerance: The max angle in degrees that the plane normals can
                differ from one another in order for them to be considered
                coplanar. (Default: 1 degree).
            orthogonal_only: A boolean to note whether only vertical and horizontal
                coplanar faces should be merged, leaving faces with any other tilt
                intact. Useful for cases where alignment of walls with the
                Room.horizontal_boundary is desired without disrupting the roof
                geometry. (Default: False).

        Returns:
            A list containing only the new Faces that were created as part of the
            merging process. These new Faces will have as many properties of the
            original Face assigned to them as possible but they will not have a
            Surface boundary condition if the original Face had one. Having
            the new Faces here can be used in operations like setting new Surface
            boundary conditions or re-assigning extension attributes.
        """
        # group the Faces of the Room by their co-planarity
        tol, a_tol = tolerance, math.radians(angle_tolerance)
        coplanar_dict = {self._faces[0].geometry.plane: [self._faces[0]]}
        if not orthogonal_only:
            for face in self._faces[1:]:
                for pln, f_list in coplanar_dict.items():
                    if face.geometry.plane.is_coplanar_tolerance(pln, tol, a_tol):
                        f_list.append(face)
                        break
                else:  # the first face with this type of plane
                    coplanar_dict[face.geometry.plane] = [face]
        else:
            up_vec = Vector3D(0, 0, 1)
            min_ang, max_ang = (math.pi / 2) - a_tol, (math.pi / 2) + a_tol
            max_h_ang = math.pi + a_tol
            for face in self._faces[1:]:
                v_ang = up_vec.angle(face.normal)
                if v_ang < a_tol or min_ang < v_ang < max_ang or v_ang > max_h_ang:
                    for pln, f_list in coplanar_dict.items():
                        if face.geometry.plane.is_coplanar_tolerance(pln, tol, a_tol):
                            f_list.append(face)
                            break
                    else:  # the first face with this type of plane
                        coplanar_dict[face.geometry.plane] = [face]
                else:
                    coplanar_dict[face.geometry.plane] = [face]

        # merge any of the coplanar Faces together
        all_faces, new_faces = [], []
        for face_list in coplanar_dict.values():
            if len(face_list) == 1:  # no faces to merge
                all_faces.append(face_list[0])
            else:  # there are faces to merge
                f_geos = [f.geometry for f in face_list]
                joined_geos = Face3D.join_coplanar_faces(f_geos, tolerance)
                if len(joined_geos) < len(f_geos):  # faces were merged
                    prop_f = face_list[0]
                    apertures, doors, in_shades, out_shades = [], [], [], []
                    for f in face_list:
                        apertures.extend(f._apertures)
                        doors.extend(f._doors)
                        in_shades.extend(f._indoor_shades)
                        out_shades.extend(f._outdoor_shades)
                    for i, new_geo in enumerate(joined_geos):
                        fid = prop_f.identifier if i == 0 else \
                            '{}_{}'.format(prop_f.identifier, i)
                        fbc = prop_f.boundary_condition if not \
                            isinstance(prop_f.boundary_condition, Surface) \
                            else boundary_conditions.outdoors
                        nf = Face(fid, new_geo, prop_f.type, fbc)
                        for ap in apertures:
                            if nf.geometry.is_sub_face(ap.geometry, tol, a_tol):
                                nf.add_aperture(ap)
                        for dr in doors:
                            if nf.geometry.is_sub_face(dr.geometry, tol, a_tol):
                                nf.add_door(dr)
                        if i == 0:  # add all assigned shades to this face
                            nf.add_indoor_shades(in_shades)
                            nf.add_outdoor_shades(out_shades)
                        nf._parent = self
                        all_faces.append(nf)
                        new_faces.append(nf)
                else:  # faces don't overlap and were not merged
                    all_faces.extend(face_list)
        if len(new_faces) == 0:
            return new_faces  # nothing has been merged

        # make a new polyface from the updated faces
        room_polyface = Polyface3D.from_faces(
            tuple(face.geometry for face in all_faces), tolerance)
        if not room_polyface.is_solid:
            room_polyface = room_polyface.merge_overlapping_edges(tolerance, a_tol)
        # replace honeybee face geometry with versions that are facing outwards
        if room_polyface.is_solid:
            for i, correct_face3d in enumerate(room_polyface.faces):
                face = all_faces[i]
                norm_init = face._geometry.normal
                face._geometry = correct_face3d
                if face.has_sub_faces:  # flip sub-faces to align with parent Face
                    if norm_init.angle(face._geometry.normal) > (math.pi / 2):
                        for ap in face._apertures:
                            ap._geometry = ap._geometry.flip()
                        for dr in face._doors:
                            dr._geometry = dr._geometry.flip()
        # reset the faces and geometry of the room with the new faces
        self._faces = tuple(all_faces)
        self._geometry = room_polyface
        return new_faces

    def coplanar_split(self, geometry, tolerance=0.01, angle_tolerance=1):
        """Split the Faces of this Room with coplanar geometry (Polyface3D or Face3D).

        This method attempts to preserve as many properties as possible for the
        split Faces, including all extension attributes and sub-faces (as long
        as they don't fall in the path of the intersection).

        Args:
            geometry: A list of coplanar geometry (either Polyface3D or Face3D)
                that will be used to split the Faces of this Room. Typically, these
                are Polyface3D of other Room geometries to be intersected with this
                one but they can also be Face3D if only one intersection is desired.
            tolerance: The minimum difference between the coordinate values of two
                faces at which they can be considered adjacent. Default: 0.01,
                suitable for objects in meters.
            angle_tolerance: The max angle in degrees that the plane normals can
                differ from one another in order for them to be considered
                coplanar. (Default: 1 degree).

        Returns:
            A list containing only the new Faces that were created as part of the
            splitting process. These new Faces will have as many properties of the
            original Face assigned to them as possible but they will not have a
            Surface boundary condition if the original Face had one. Having just
            the new Faces here can be used in operations like setting new Surface
            boundary conditions.
        """
        # make a dictionary of all face geometry to be intersected
        geo_dict = {f.identifier: [f.geometry] for f in self.faces}

        # loop through the polyface geometries and intersect this room's geometry
        ang_tol = math.radians(angle_tolerance)
        for s_geo in geometry:
            if isinstance(s_geo, Polyface3D) and not \
                    Polyface3D.overlapping_bounding_boxes(
                        self.geometry, s_geo, tolerance):
                continue  # no overlap in bounding box; intersection impossible
            s_geos = s_geo.faces if isinstance(s_geo, Polyface3D) else [s_geo]
            for face_1 in self.faces:
                for face_2 in s_geos:
                    if not face_1.geometry.plane.is_coplanar_tolerance(
                            face_2.plane, tolerance, ang_tol):
                        continue  # not coplanar; intersection impossible
                    if face_1.geometry.is_centered_adjacent(face_2, tolerance):
                        tol_area = math.sqrt(face_1.geometry.area) * tolerance
                        if abs(face_1.geometry.area - face_2.area) < tol_area:
                            continue  # already intersected; no need to re-do
                    new_geo = []
                    for f_geo in geo_dict[face_1.identifier]:
                        f_split, _ = Face3D.coplanar_split(
                            f_geo, face_2, tolerance, ang_tol)
                        for sp_g in f_split:
                            try:
                                sp_g = sp_g.remove_colinear_vertices(tolerance)
                                new_geo.append(sp_g)
                            except AssertionError:  # degenerate geometry to ignore
                                pass
                    geo_dict[face_1.identifier] = new_geo

        # use the intersected geometry to remake this room's faces
        all_faces, new_faces = [], []
        for face in self.faces:
            int_faces = geo_dict[face.identifier]
            if len(int_faces) == 1:  # just use the old Face object
                all_faces.append(face)
            else:  # make new Face objects
                new_bc = face.boundary_condition \
                    if not isinstance(face.boundary_condition, Surface) \
                    else boundary_conditions.outdoors
                new_aps = [ap.duplicate() for ap in face.apertures]
                new_drs = [dr.duplicate() for dr in face.doors]
                for x, nf_geo in enumerate(int_faces):
                    new_id = '{}_{}'.format(face.identifier, x)
                    new_face = Face(new_id, nf_geo, face.type, new_bc)
                    new_face._display_name = face._display_name
                    new_face._user_data = None if face.user_data is None \
                        else face.user_data.copy()
                    for ap in new_aps:
                        if nf_geo.is_sub_face(ap.geometry, tolerance, ang_tol):
                            new_face.add_aperture(ap)
                    for dr in new_drs:
                        if nf_geo.is_sub_face(dr.geometry, tolerance, ang_tol):
                            new_face.add_door(dr)
                    if x == 0:
                        face._duplicate_child_shades(new_face)
                    new_face._parent = face._parent
                    new_face._properties._duplicate_extension_attr(face._properties)
                    new_faces.append(new_face)
                    all_faces.append(new_face)
        if len(new_faces) == 0:
            return new_faces  # nothing has been intersected

        # make a new polyface from the updated faces
        room_polyface = Polyface3D.from_faces(
            tuple(face.geometry for face in all_faces), tolerance)
        if not room_polyface.is_solid:
            room_polyface = room_polyface.merge_overlapping_edges(tolerance, ang_tol)
        # replace honeybee face geometry with versions that are facing outwards
        if room_polyface.is_solid:
            for i, correct_face3d in enumerate(room_polyface.faces):
                face = all_faces[i]
                norm_init = face._geometry.normal
                face._geometry = correct_face3d
                if face.has_sub_faces:  # flip sub-faces to align with parent Face
                    if norm_init.angle(face._geometry.normal) > (math.pi / 2):
                        for ap in face._apertures:
                            ap._geometry = ap._geometry.flip()
                        for dr in face._doors:
                            dr._geometry = dr._geometry.flip()
        # reset the faces and geometry of the room with the new faces
        self._faces = tuple(all_faces)
        self._geometry = room_polyface
        return new_faces

    @staticmethod
    def intersect_adjacency(rooms, tolerance=0.01, angle_tolerance=1):
        """Intersect the Faces of an array of Rooms to ensure matching adjacencies.

        Note that this method may remove Apertures and Doors if they align with
        an intersection so it is typically recommended that this method be used
        before sub-faces are assigned (if possible). Sub-faces that do not fall
        along an intersection will be preserved.

        Also note that this method does not actually set the walls that are next to one
        another to be adjacent. The solve_adjacency method must be used for this after
        running this method.

        Args:
            rooms: A list of Rooms for which adjacent Faces will be intersected.
            tolerance: The minimum difference between the coordinate values of two
                faces at which they can be considered adjacent. Default: 0.01,
                suitable for objects in meters.
            angle_tolerance: The max angle in degrees that the plane normals can
                differ from one another in order for them to be considered
                coplanar. (Default: 1 degree).

        Returns:
            An array of Rooms that have been intersected with one another.
        """
        # get all of the room polyfaces
        room_geos = [r.geometry for r in rooms]
        # intersect all adjacencies between rooms
        for i, room in enumerate(rooms):
            other_rooms = room_geos[:i] + room_geos[i + 1:]
            room.coplanar_split(other_rooms, tolerance, angle_tolerance)

    @staticmethod
    def solve_adjacency(rooms, tolerance=0.01):
        """Solve for adjacencies between a list of rooms.

        Note that this method will mutate the input rooms by setting Surface
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
                pass  # we have reached the end of the list of rooms
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
    def group_by_adjacency(rooms):
        """Group Rooms together that are connected by adjacencies.

        This is useful for separating rooms in the case where a Model contains
        multiple buildings or sections that are separated by adiabatic or
        outdoor boundary conditions.

        Args:
            rooms: A list of rooms to be grouped by their adjacency.

        Returns:
            A list of list with each sub-list containing rooms that share adjacencies.
        """
        return Room._adjacency_grouping(rooms, Room._find_adjacent_rooms)

    @staticmethod
    def group_by_air_boundary_adjacency(rooms):
        """Group Rooms together that share air boundaries.

        This is useful for understanding the radiant enclosures that will exist
        when a model is exported to EnergyPlus.

        Args:
            rooms: A list of rooms to be grouped by their air boundary adjacency.

        Returns:
            A list of list with each sub-list containing rooms that share adjacent
            air boundaries. If a Room has no air boundaries it will the the only
            item within its sub-list.
        """
        return Room._adjacency_grouping(rooms, Room._find_adjacent_air_boundary_rooms)

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

    @staticmethod
    def check_room_volume_collisions(rooms, tolerance=0.01, detailed=False):
        """Check whether the volumes of Rooms collide with one another beyond tolerance.

        At the moment, this method only checks for the case where coplanar Floor
        Faces of different Rooms overlap with one another, which clearly indicates
        that there is definitely a collision between the Room volumes. In the
        future, this method may be amended to sense more complex cases of
        colliding Room volumes. For now, it is designed to only detect the most
        common cases.

        Args:
            rooms: A list of rooms that will be checked for volumetric collisions.
                For this method to run most efficiently, these input Rooms should
                be at the same horizontal floor level. The Room.group_by_floor_height()
                method can be used to group the Rooms of a model according to their
                height before running this method.
            tolerance: The minimum difference between the coordinate values of two
                vertices at which they can be considered equivalent. (Default: 0.01,
                suitable for objects in meters.
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        # create Polygon2Ds from the floors of the rooms
        polys = [
            [(Polygon2D(Point2D(p.x, p.y) for p in flr.vertices), flr.geometry[0].z)
             for flr in room.floors if flr.geometry.is_horizontal(tolerance)]
            for room in rooms
        ]

        # find the number of overlaps across the Rooms
        msgs = []
        for i, (room_1, polys_1) in enumerate(zip(rooms, polys)):
            overlap_rooms = []
            if len(polys_1) == 0:
                continue
            try:
                for room_2, polys_2 in zip(rooms[i + 1:], polys[i + 1:]):
                    collision_found = False
                    for ply_1, z1 in polys_1:
                        if collision_found:
                            break
                        for ply_2, z2 in polys_2:
                            if collision_found:
                                break
                            if abs(z1 - z2) < tolerance:
                                if ply_1.polygon_relationship(ply_2, tolerance) >= 0:
                                    overlap_rooms.append(room_2)
                                    collision_found = True
                                    break
            except IndexError:
                pass  # we have reached the end of the list

            # of colliding rooms were found, create error messages
            if len(overlap_rooms) != 0:
                for room_2 in overlap_rooms:
                    msg = 'Room "{}" has a volume that collides with the volume ' \
                        'of Room "{}" more than the tolerance ({}).'.format(
                            room_1.display_name, room_2.display_name, tolerance)
                    msg = Room._validation_message_child(
                        msg, room_1, detailed, '000108',
                        error_type='Colliding Room Volumes')
                    if detailed:
                        msg['element_id'].append(room_2.identifier)
                        msg['element_name'].append(room_2.display_name)
                        msg['parents'].append(msg['parents'][0])
                    msgs.append(msg)
        # report any errors
        if detailed:
            return msgs
        full_msg = '\n '.join(msgs)
        return full_msg

    @staticmethod
    def grouped_horizontal_boundary(
            rooms, min_separation=0, tolerance=0.01, floors_only=True):
        """Get a list of Face3D for the horizontal boundary around several Rooms.

        This method will attempt to produce a boundary that follows along the
        outer parts of the Floors of the Rooms so it is not suitable for groups
        of Rooms that overlap one another in plan. This method may return an empty
        list if the min_separation is so large that a continuous boundary could not
        be determined.

        Args:
            rooms: A list of Honeybee Rooms for which the horizontal boundary will
                be computed.
            min_separation: A number for the minimum distance between Rooms that
                is considered a meaningful separation. Gaps between Rooms that
                are less than this distance will be ignored and the boundary
                will continue across the gap. When the input rooms represent
                volumes of interior Faces, this input can be thought of as the
                maximum interior wall thickness, which should be ignored in
                the calculation of the overall boundary of the Rooms. When Rooms
                are touching one another (with Room volumes representing center lines
                of walls), this value can be set to zero or anything less than
                or equal to the tolerance. Doing so will yield a cleaner result for
                the boundary, which will be faster. Note that care should be taken
                not to set this value higher than the length of any meaningful
                exterior wall segments. Otherwise, the exterior segments
                will be ignored in the result. This can be particularly dangerous
                around curved exterior walls that have been planarized through
                subdivision into small segments. (Default: 0).
            tolerance: The maximum difference between coordinate values of two
                vertices at which they can be considered equivalent. (Default: 0.01,
                suitable for objects in meters).
            floors_only: A boolean to note whether the grouped boundary should only
                surround the Floor geometries of the Rooms (True) or if they should
                surround the entirety of the Room volumes in plan (False).
        """
        # get the horizontal boundary geometry of each room
        floor_geos = []
        if floors_only:
            for room in rooms:
                floor_geos.extend(room.horizontal_floor_boundaries(tolerance=tolerance))
        else:
            for room in rooms:
                floor_geos.append(room.horizontal_boundary(tolerance=tolerance))

        # remove colinear vertices and degenerate faces
        clean_floor_geos = []
        for geo in floor_geos:
            try:
                clean_floor_geos.append(geo.remove_colinear_vertices(tolerance))
            except AssertionError:  # degenerate geometry to ignore
                pass
        if len(clean_floor_geos) == 0:
            return []  # no Room boundary to be found

        # convert the floor Face3Ds into counterclockwise Polygon2Ds
        floor_polys, z_vals = [], []
        for flr_geo in clean_floor_geos:
            z_vals.append(flr_geo.min.z)
            b_poly = Polygon2D([Point2D(pt.x, pt.y) for pt in flr_geo.boundary])
            floor_polys.append(b_poly)
            if flr_geo.has_holes:
                for hole in flr_geo.holes:
                    h_poly = Polygon2D([Point2D(pt.x, pt.y) for pt in hole])
                    floor_polys.append(h_poly)
        z_min = min(z_vals)

        # if the min_separation is small, use the more reliable intersection method
        if min_separation <= tolerance:
            closed_polys = Polygon2D.joined_intersected_boundary(floor_polys, tolerance)
        else:  # otherwise, use the more intense and less reliable gap crossing method
            closed_polys = Polygon2D.gap_crossing_boundary(
                floor_polys, min_separation, tolerance)

        # remove colinear vertices from the resulting polygons
        clean_polys = []
        for poly in closed_polys:
            try:
                clean_polys.append(poly.remove_colinear_vertices(tolerance))
            except AssertionError:
                pass  # degenerate polygon to ignore

        # figure out if polygons represent holes in the others and make Face3D
        if len(clean_polys) == 0:
            return []
        elif len(clean_polys) == 1:  # can be represented with a single Face3D
            pts3d = [Point3D(pt.x, pt.y, z_min) for pt in clean_polys[0]]
            return [Face3D(pts3d)]
        else:  # need to separate holes from distinct Face3Ds
            bound_faces = []
            for poly in clean_polys:
                pts3d = tuple(Point3D(pt.x, pt.y, z_min) for pt in poly)
                bound_faces.append(Face3D(pts3d))
            return Face3D.merge_faces_to_holes(bound_faces, tolerance)

    @staticmethod
    def rooms_from_rectangle_plan(
            width, length, floor_to_floor_height, perimeter_offset=0, story_count=1,
            orientation_angle=0, outdoor_roof=True, ground_floor=True,
            unique_id=None, tolerance=0.01):
        """Create a Rooms that represent a rectangular floor plan.

        Note that the resulting Rooms won't have any windows or solved adjacencies.
        These can be added by using the Room.solve_adjacency method and the
        various Face.apertures_by_XXX methods.

        Args:
            width: Number for the width of the plan (in the X direction).
            length: Number for the length of the plan (in the Y direction).
            floor_to_floor_height: Number for the height of each floor of the model
                (in the Z direction).
            perimeter_offset: An optional positive number that will be used to offset
                the perimeter to create core/perimeter Rooms. If this value is 0,
                no offset will occur and each floor will have one Room. (Default: 0).
            story_count: An integer for the number of stories to generate. (Default: 1).
            orientation_angle: A number between 0 and 360 for the counterclockwise
                orientation that the width of the box faces. (0=North, 90=East,
                180=South, 270=West). (Default: 0).
            outdoor_roof: Boolean to note whether the roof faces of the top floor
                should be outdoor or adiabatic. (Default: True).
            ground_floor: Boolean to note whether the floor faces of the bottom
                floor should be ground or adiabatic. (Default: True).
            unique_id: Text for a unique identifier to be incorporated into all
                of the Room identifiers. If None, a default one will be generated.
            tolerance: The maximum difference between x, y, and z values at which
                vertices are considered equivalent. (Default: 0.01, suitable
                for objects in meters).
        """
        footprint = [Face3D.from_rectangle(width, length)]
        if perimeter_offset != 0:  # use the straight skeleton methods
            assert perimeter_offset > 0, 'perimeter_offset cannot be less than than 0.'
            try:
                footprint = []
                base = Polygon2D.from_rectangle(Point2D(), Vector2D(0, 1), width, length)
                sub_polys_perim, sub_polys_core = perimeter_core_subpolygons(
                    polygon=base, distance=perimeter_offset, tolerance=tolerance)
                for s_poly in sub_polys_perim + sub_polys_core:
                    sub_face = Face3D([Point3D(pt.x, pt.y, 0) for pt in s_poly])
                    footprint.append(sub_face)
            except RuntimeError:
                pass
        # create the honeybee rooms
        if unique_id is None:
            unique_id = str(uuid.uuid4())[:8]  # unique identifier for the rooms
        rm_ids = ['Room'] if len(footprint) == 1 else ['Front', 'Right', 'Back', 'Left']
        if len(footprint) == 5:
            rm_ids.append('Core')
        return Room.rooms_from_footprint(
            footprint, floor_to_floor_height, rm_ids, unique_id, orientation_angle,
            story_count, outdoor_roof, ground_floor)

    @staticmethod
    def rooms_from_l_shaped_plan(
            width_1, length_1, width_2, length_2, floor_to_floor_height,
            perimeter_offset=0, story_count=1, orientation_angle=0,
            outdoor_roof=True, ground_floor=True, unique_id=None, tolerance=0.01):
        """Create a Rooms that represent an L-shaped floor plan.

        Note that the resulting Rooms in the model won't have any windows or solved
        adjacencies. These can be added by using the Room.solve_adjacency method
        and the various Face.apertures_by_XXX methods.

        Args:
            width_1: Number for the width of the lower part of the L segment.
            length_1: Number for the length of the lower part of the L segment, not
                counting the overlap between the upper and lower segments.
            width_2: Number for the width of the upper (left) part of the L segment.
            length_2: Number for the length of the upper (left) part of the L segment,
                not counting the overlap between the upper and lower segments.
            floor_to_floor_height: Number for the height of each floor of the model
                (in the Z direction).
            perimeter_offset: An optional positive number that will be used to offset
                the perimeter to create core/perimeter Rooms. If this value is 0,
                no offset will occur and each floor will have one Room. (Default: 0).
            story_count: An integer for the number of stories to generate. (Default: 1).
            orientation_angle: A number between 0 and 360 for the counterclockwise
                orientation that the width of the box faces. (0=North, 90=East,
                180=South, 270=West). (Default: 0).
            outdoor_roof: Boolean to note whether the roof faces of the top floor
                should be outdoor or adiabatic. (Default: True).
            ground_floor: Boolean to note whether the floor faces of the bottom
                floor should be ground or adiabatic. (Default: True).
            unique_id: Text for a unique identifier to be incorporated into all
                of the Room identifiers. If None, a default one will be generated.
            tolerance: The maximum difference between x, y, and z values at which
                vertices are considered equivalent. (Default: 0.01, suitable
                for objects in meters).
        """
        # create the geometry of the rooms for the first floor
        max_x, max_y = width_2 + length_1, width_1 + length_2
        pts = [(0, 0), (max_x, 0), (max_x, width_1), (width_2, width_1),
               (width_2, max_y), (0, max_y)]
        footprint = Face3D(tuple(Point3D(*pt) for pt in pts))
        if perimeter_offset != 0:  # use the straight skeleton methods
            assert perimeter_offset > 0, 'perimeter_offset cannot be less than than 0.'
            try:
                footprint = []
                base = Polygon2D(tuple(Point2D(*pt) for pt in pts))
                sub_polys_perim, sub_polys_core = perimeter_core_subpolygons(
                    polygon=base, distance=perimeter_offset, tolerance=tolerance)
                for s_poly in sub_polys_perim + sub_polys_core:
                    sub_face = Face3D([Point3D(pt.x, pt.y, 0) for pt in s_poly])
                    footprint.append(sub_face)
            except RuntimeError:
                pass
        # create the honeybee rooms
        unique_id = '' if unique_id is None else '_{}'.format(unique_id)
        rm_ids = ['Room'] if len(footprint) == 1 else \
            ['LongEdge1', 'End1', 'ShortEdge1', 'ShortEdge2', 'End2', 'LongEdge2']
        if len(footprint) == 7:
            rm_ids.append('Core')
        return Room.rooms_from_footprint(
            footprint, floor_to_floor_height, rm_ids, unique_id, orientation_angle,
            story_count, outdoor_roof, ground_floor)

    @staticmethod
    def rooms_from_footprint(
            footprints, floor_to_floor_height, room_ids=None, unique_id=None,
            orientation_angle=0, story_count=1, outdoor_roof=True, ground_floor=True):
        """Create several Honeybee Rooms from footprint Face3Ds.

        Args:
            footprints: A list of Face3Ds representing the floors of Rooms.
            floor_to_floor_height: Number for the height of each floor of the model
                (in the Z direction).
            room_ids: A list of strings for the identifiers of the Rooms to be generated.
                If None, default unique IDs will be generated. (Default: None)
            unique_id: Text for a unique identifier to be incorporated into all
                Room identifiers. (Default: None).
            orientation_angle: A number between 0 and 360 for the counterclockwise
                orientation that the width of the box faces. (0=North, 90=East,
                180=South, 270=West). (Default: 0).
            story_count: An integer for the number of stories to generate. (Default: 1).
            outdoor_roof: Boolean to note whether the roof faces of the top floor
                should be outdoor or adiabatic. (Default: True).
            ground_floor: Boolean to note whether the floor faces of the bottom
                floor should be ground or adiabatic. (Default: True).
        """
        # set default identifiers if not provided
        if room_ids is None:
            room_ids = ['Room_{}'.format(str(uuid.uuid4())[:8]) for _ in footprints]
        # extrude the footprint into solids
        first_floor = [Polyface3D.from_offset_face(geo, floor_to_floor_height)
                       for geo in footprints]
        # rotate the geometries if an orientation angle is specified
        if orientation_angle != 0:
            angle, origin = math.radians(orientation_angle), Point3D()
            first_floor = [geo.rotate_xy(angle, origin) for geo in first_floor]
        # create the initial rooms for the first floor
        rooms = []
        unique_id = '' if unique_id is None else '_{}'.format(unique_id)
        for polyface, rmid in zip(first_floor, room_ids):
            rooms.append(Room.from_polyface3d('{}{}'.format(rmid, unique_id), polyface))
        # if there are multiple stories, duplicate the first floor rooms
        if story_count != 1:
            all_rooms = []
            for i in range(story_count):
                for room in rooms:
                    new_room = room.duplicate()
                    new_room.add_prefix('Floor{}'.format(i + 1))
                    m_vec = Vector3D(0, 0, floor_to_floor_height * i)
                    new_room.move(m_vec)
                    all_rooms.append(new_room)
            rooms = all_rooms
        # assign readable names for the display_name (without the UUID)
        for room in rooms:
            room.display_name = room.identifier[:-9]
        # assign adiabatic boundary conditions if requested
        if not outdoor_roof and ad_bc:
            for room in rooms[-len(first_floor):]:
                room[-1].boundary_condition = ad_bc  # make the roof adiabatic
        if not ground_floor and ad_bc:
            for room in rooms[:len(first_floor)]:
                room[0].boundary_condition = ad_bc  # make the floor adiabatic
        return rooms

    def display_dict(self):
        """Get a list of DisplayFace3D dictionaries for visualizing the object."""
        base = []
        for f in self._faces:
            base.extend(f.display_dict())
        for shd in self.shades:
            base.extend(shd.display_dict())
        return base

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

    def to_dict(self, abridged=False, included_prop=None, include_plane=True):
        """Return Room as a dictionary.

        Args:
            abridged: Boolean to note whether the extension properties of the
                object (ie. construction sets) should be included in detail
                (False) or just referenced by identifier (True). Default: False.
            included_prop: List of properties to filter keys that must be included in
                output dictionary. For example ['energy'] will include 'energy' key if
                available in properties to_dict. By default all the keys will be
                included. To exclude all the keys from extensions use an empty list.
            include_plane: Boolean to note wether the planes of the Face3Ds should be
                included in the output. This can preserve the orientation of the
                X/Y axes of the planes but is not required and can be removed to
                keep the dictionary smaller. (Default: True).
        """
        base = {'type': 'Room'}
        base['identifier'] = self.identifier
        base['display_name'] = self.display_name
        base['properties'] = self.properties.to_dict(abridged, included_prop)
        base['faces'] = [f.to_dict(abridged, included_prop, include_plane)
                         for f in self._faces]
        self._add_shades_to_dict(base, abridged, included_prop, include_plane)
        if self.multiplier != 1:
            base['multiplier'] = self.multiplier
        if self.story is not None:
            base['story'] = self.story
        if self.exclude_floor_area:
            base['exclude_floor_area'] = self.exclude_floor_area
        if self.user_data is not None:
            base['user_data'] = self.user_data
        return base

    def _base_horiz_boundary(self, tolerance=0.01):
        """Get a starting horizontal boundary for the Room.

        This is the raw result obtained by merging all downward-facing Faces of the Room.

        Args:
            tolerance: The minimum difference between x, y, and z coordinate values
                at which points are considered distinct. (Default: 0.01,
                suitable for objects in Meters).
        """
        z_axis = Vector3D(0, 0, 1)
        flr_geo = []
        for face in self.faces:
            if math.degrees(z_axis.angle(face.normal)) >= 91:
                flr_geo.append(face.geometry)
        if len(flr_geo) == 1:
            if flr_geo[0].is_horizontal(tolerance):
                return flr_geo[0]
            else:
                floor_height = self.geometry.min.z
                bound = [Point3D(p.x, p.y, floor_height) for p in flr_geo[0].boundary]
                holes = None
                if flr_geo[0].has_holes:
                    holes = [[Point3D(p.x, p.y, floor_height) for p in hole]
                             for hole in flr_geo[0].holes]
                return Face3D(bound, holes=holes)
        else:  # multiple geometries to be joined together
            floor_height = self.geometry.min.z
            horiz_geo = []
            for fg in flr_geo:
                if fg.is_horizontal(tolerance) and \
                        abs(floor_height - fg.min.z) <= tolerance:
                    horiz_geo.append(fg)
                else:  # project the face geometry into the XY plane
                    bound = [Point3D(p.x, p.y, floor_height) for p in fg.boundary]
                    holes = None
                    if fg.has_holes:
                        holes = [[Point3D(p.x, p.y, floor_height) for p in hole]
                                 for hole in fg.holes]
                    horiz_geo.append(Face3D(bound, holes=holes))
            # sense if there are overlapping geometries to be boolean unioned
            overlap_groups = Face3D.group_by_coplanar_overlap(horiz_geo, tolerance)
            if all(len(g) == 1 for g in overlap_groups):  # no overlaps; just join
                return Face3D.join_coplanar_faces(horiz_geo, tolerance)[0]
            # we must do a boolean union
            clean_geo = []
            for og in overlap_groups:
                if len(og) == 1:
                    clean_geo.extend(og)
                else:
                    a_tol = math.radians(1)
                    union = Face3D.coplanar_union_all(og, tolerance, a_tol)
                    if len(union) == 1:
                        clean_geo.extend(union)
                    else:
                        sort_geo = sorted(union, key=lambda x: x.area, reverse=True)
                        clean_geo.append(sort_geo[0])
            if len(clean_geo) == 1:
                return clean_geo[0]
            return Face3D.join_coplanar_faces(clean_geo, tolerance)[0]

    def _match_walls_to_horizontal_faces(self, faces, tolerance):
        """Insert vertices to horizontal faces so they align with the Room's Walls.

        Args:
            faces: A list of Face3D into which the vertices of the walls will
                be inserted.
            tolerance: The minimum difference between x, y, and z coordinate values
                at which points are considered distinct. (Default: 0.01,
                suitable for objects in Meters).
        """
        # get 2D vertices for all of the walls
        wall_st_pts = [
            f.geometry.lower_left_counter_clockwise_vertices[0] for f in self.walls]
        wall_st_pts_2d = [Point2D(v[0], v[1]) for v in wall_st_pts]
        # insert the wall points into each of the faces
        wall_faces = []
        for horiz_bound in faces:
            # get 2D polygons for the horizontal boundary
            z_val = horiz_bound[0].z
            polys = [Polygon2D([Point2D(v.x, v.y) for v in horiz_bound.boundary])]
            if horiz_bound.holes is not None:
                for hole in horiz_bound.holes:
                    polys.append(Polygon2D([Point2D(v.x, v.y) for v in hole]))
            # insert the wall vertices into the polygon
            wall_polys = []
            for st_poly in polys:
                st_poly = st_poly.remove_colinear_vertices(tolerance)
                polygon_update = []
                for pt in wall_st_pts_2d:
                    for v in st_poly.vertices:  # check if pt is already included
                        if pt.is_equivalent(v, tolerance):
                            break
                    else:
                        values = [seg.distance_to_point(pt) for seg in st_poly.segments]
                        if min(values) < tolerance:
                            index_min = min(range(len(values)), key=values.__getitem__)
                            polygon_update.append((index_min, pt))
                if polygon_update:
                    end_poly = Polygon2D._insert_updates_in_order(st_poly, polygon_update)
                    wall_polys.append(end_poly)
                else:
                    wall_polys.append(st_poly)
            # rebuild the Face3D from the polygons
            pts_3d = [[Point3D(p.x, p.y, z_val) for p in poly] for poly in wall_polys]
            wall_faces.append(Face3D(pts_3d[0], holes=pts_3d[1:]))
        return wall_faces

    @staticmethod
    def _adjacency_grouping(rooms, adj_finding_function):
        """Group Rooms together according to an adjacency finding function.

        Args:
            rooms: A list of rooms to be grouped by their adjacency.
            adj_finding_function: A function that denotes which rooms are adjacent
                to another.

        Returns:
            A list of list with each sub-list containing rooms that share adjacencies.
        """
        # create a room lookup table and duplicate the list of rooms
        room_lookup = {rm.identifier: rm for rm in rooms}
        all_rooms = list(rooms)
        adj_network = []

        # loop through the rooms and find air boundary adjacencies
        for room in all_rooms:
            adj_ids = adj_finding_function(room)
            if len(adj_ids) == 0:  # a room that is its own solar enclosure
                adj_network.append([room])
            else:  # there are other adjacent rooms to find
                local_network = [room]
                local_ids, first_id = set(adj_ids), room.identifier
                while len(adj_ids) != 0:
                    # add the current rooms to the local network
                    adj_objs = [room_lookup[rm_id] for rm_id in adj_ids]
                    local_network.extend(adj_objs)
                    adj_ids = []  # reset the list of new adjacencies
                    # find any rooms that are adjacent to the adjacent rooms
                    for obj in adj_objs:
                        all_new_ids = adj_finding_function(obj)
                        new_ids = [rid for rid in all_new_ids
                                   if rid not in local_ids and rid != first_id]
                        for rm_id in new_ids:
                            local_ids.add(rm_id)
                        adj_ids.extend(new_ids)
                # after the local network is understood, clean up duplicated rooms
                adj_network.append(local_network)
                i_to_remove = [i for i, room_obj in enumerate(all_rooms)
                               if room_obj.identifier in local_ids]
                for i in reversed(i_to_remove):
                    all_rooms.pop(i)
        return adj_network

    @staticmethod
    def _find_adjacent_rooms(room):
        """Find the identifiers of all rooms with adjacency to a room."""
        adj_rooms = []
        for face in room._faces:
            if isinstance(face.boundary_condition, Surface):
                adj_rooms.append(face.boundary_condition.boundary_condition_objects[-1])
        return adj_rooms

    @staticmethod
    def _find_adjacent_air_boundary_rooms(room):
        """Find the identifiers of all rooms with air boundary adjacency to a room."""
        adj_rooms = []
        for face in room._faces:
            if isinstance(face.type, AirBoundary) and \
                    isinstance(face.boundary_condition, Surface):
                adj_rooms.append(face.boundary_condition.boundary_condition_objects[-1])
        return adj_rooms

    def __copy__(self):
        new_r = Room(self.identifier, tuple(face.duplicate() for face in self._faces))
        new_r._display_name = self._display_name
        new_r._user_data = None if self.user_data is None else self.user_data.copy()
        new_r._multiplier = self.multiplier
        new_r._story = self.story
        new_r._exclude_floor_area = self.exclude_floor_area
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
