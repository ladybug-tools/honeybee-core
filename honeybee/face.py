# coding: utf-8
"""Honeybee Face."""
from .properties import FaceProperties
from .facetype import face_types, get_type_from_normal, AirWall
from .boundarycondition import get_bc_from_position, _BoundaryCondition, \
    Outdoors, Surface
from .shade import Shade
from .aperture import Aperture
from .door import Door
from .typing import valid_string
import honeybee.writer as writer

from ladybug_geometry.geometry2d.pointvector import Point2D, Vector2D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.plane import Plane
from ladybug_geometry.geometry3d.face import Face3D

import math


class Face(object):
    """A single planar face.

    Properties:
        name
        name_original
        geometry
        punched_geometry
        vertices
        punched_vertices
        upper_left_vertices
        normal
        center
        area
        perimeter
        type
        boundary_condition
        apertures
        doors
        parent
        has_parent
    """
    TYPES = face_types
    __slots__ = ('_name', '_name_original', '_geometry', '_parent', '_punched_geometry',
                 '_apertures', '_doors', '_type', '_boundary_condition', '_properties')

    def __init__(self, name, geometry, type=None, boundary_condition=None):
        """A single planar face.

        Args:
            name: Face name. Must be < 100 characters.
            geometry: A ladybug-geometry Face3D.
            type: Face type. Default varies depending on the direction that
                the Face geometry is points.
                RoofCeiling = pointing upward within 30 degrees
                Wall = oriented vertically within +/- 60 degrees
                Floor = pointing downward within 30 degrees
            boundary_condition: Face boundary condition (Outdoors, Ground, etc.)
                Default is Outdoors unless the center of the input geometry lies
                below the XY plane, in which case it will be set to Ground.
        """
        # process the name
        self._name = valid_string(name, 'honeybee face name')
        self._name_original = name

        # process the geometry
        assert isinstance(geometry, Face3D), \
            'Expected ladybug_geometry Face3D. Got {}'.format(type(geometry))
        self._geometry = geometry
        self._parent = None  # _parent will be set when the Face is added to a Room
        # initialize with no apertures/doors (they can be assigned later)
        self._punched_geometry = None
        self._apertures = []
        self._doors = []

        # set face type based on normal if not provided
        self.type = type or get_type_from_normal(geometry.normal)

        # set boundary condition by the relation to a zero ground plane if not provided
        self.boundary_condition = boundary_condition or \
            get_bc_from_position(geometry.boundary)

        # initialize properties for extensions
        self._properties = FaceProperties(self)

    @classmethod
    def from_vertices(cls, name, vertices, type=None, boundary_condition=None):
        """Create a Face from vertices with each vertex as an iterable of 3 floats.

        Note that this method is not recommended for a face with one or more holes
        since the distinction between hole vertices and boundary vertices cannot
        be derived from a single list of vertices.

        Args:
            name: Face name.
            vertices: A flattened list of 3 or more vertices as (x, y, z).
            type: Face type object (eg. Wall, Floor).
            boundary_condition: Boundary condition object (eg. Outdoors, Surface)
        """
        geometry = Face3D(tuple(Point3D(*v) for v in vertices))
        return cls(name, geometry, type, boundary_condition)

    @property
    def name(self):
        """The face name (including only legal characters)."""
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
    def geometry(self):
        """A ladybug_geometry Face3D object representing the Face.

        Note that this Face3D only represents the parent face and does not have any
        holes cut in it for apertures or doors.
        """
        return self._geometry

    @property
    def punched_geometry(self):
        """A ladybug_geometry Face3D object with holes cut in it for apertures and doors.
        """
        if self._punched_geometry is None:
            _sub_faces = tuple(sub_f.geometry for sub_f in self._apertures + self._doors)
            if _sub_faces != []:
                self._punched_geometry = Face3D.from_punched_geometry(
                    self._geometry, _sub_faces)
            else:
                self._punched_geometry = self._geometry
        return self._punched_geometry

    @property
    def vertices(self):
        """List of vertices for the face (in counter-clockwise order).

        Note that these vertices only represent the outer boundary of the face
        and do not account for holes cut in the face by apertures or doors.
        """
        return self._geometry.vertices

    @property
    def punched_vertices(self):
        """List of vertices with holes cut in it for apertures and doors.

        Note that some vertices will be repeated since the vertices effectively
        trace out a single boundary around the whole shape, winding inward to cut
        out the holes. This property should be used  when exporting to Radiance.
        """
        return self.punched_geometry.vertices

    @property
    def upper_left_vertices(self):
        """List of vertices starting from the upper-left corner.

        This property obeys the same rules as the vertices property but always starts
        from the upper-left-most vertex.  This property should be used when exporting to
        EnergyPlus / OpenStudio.
        """
        return self._geometry.upper_left_counter_clockwise_vertices

    @property
    def normal(self):
        """A ladybug_geometry Vector3D for the direction in which the face is pointing.
        """
        return self._geometry.normal

    @property
    def center(self):
        """A ladybug_geometry Point3D for the center of the face.

        Note that this is the center of the bounding rectangle around this geometry
        and not the area centroid.
        """
        return self._geometry.center

    @property
    def area(self):
        """The area of the face."""
        return self._geometry.area

    @property
    def perimeter(self):
        """The perimeter of the face. This includes the length of holes in the face."""
        return self._geometry.perimeter

    @property
    def type(self):
        """Object for Type of Face (ie. Wall, Floor, Roof)."""
        return self._type

    @type.setter
    def type(self, value):
        assert value in self.TYPES, '{} is not a valid face type.'.format(value)
        if self._apertures != [] or self._doors != []:
            assert not isinstance(value, AirWall), \
                '{} cannot be assigned to a Face with Apertures or Doors.'.format(value)
        self._type = value

    @property
    def boundary_condition(self):
        """Object for the Face Boundary Condition (ie. Outdoors, Surface, Ground)."""
        return self._boundary_condition

    @boundary_condition.setter
    def boundary_condition(self, value):
        assert isinstance(value, _BoundaryCondition), \
            'Expected BoundaryCondition. Got {}'.format(type(value))
        if self._apertures != [] or self._doors != []:
            assert isinstance(value, (Outdoors, Surface)), \
                '{} cannot be assigned to a Face with apertures or doors.'.format(value)
        self._boundary_condition = value

    @property
    def apertures(self):
        """List of apertures in this Face."""
        return tuple(self._apertures)

    @property
    def doors(self):
        """List of doors in this Face."""
        return tuple(self._doors)

    @property
    def parent(self):
        """Parent Room if assigned. None if not assigned."""
        return self._parent

    @property
    def has_parent(self):
        """Boolean noting whether this Face has a parent Room."""
        return self._parent is not None

    def horizontal_orientation(self, north_vector=Vector2D(0, 1)):
        """A number between 0 and 360 for the orientation of the face in degrees.

        0 = North, 90 = East, 180 = South, 270 = West

        Args:
            north_vector: A ladybug_geometry Vector2D for the north direction.
                Default is the Y-axis (0, 1).
        """
        return math.degrees(
            north_vector.angle_clockwise(Vector2D(self.normal.x, self.normal.y)))

    def cardinal_direction(self, north_vector=Vector2D(0, 1)):
        """Text description for the cardinal direction that the face is pointing.

        Will be one of the following: ('North', 'East', 'South', 'West')

        Args:
            north_vector: A ladybug_geometry Vector2D for the north direction.
                Default is the Y-axis (0, 1).
        """
        orient = self.horizontal_orientation(north_vector)
        if orient <= 45 or orient > 315:
            return 'North'
        elif orient <= 135:
            return 'East'
        elif orient <= 225:
            return 'South'
        else:
            return 'West'

    def clear_sub_faces(self):
        """Remove all apertures and doors from the face."""
        self.clear_apertures()
        self.clear_doors()

    def clear_apertures(self):
        """Remove all apertures from the face."""
        for aperture in self._apertures:
            aperture._parent = None
        self._apertures = []
        self._punched_geometry = None  # reset so that it can be re-computed

    def clear_doors(self):
        """Remove all doors from the face."""
        for door in self._apertures:
            door._parent = None
        self._doors = []
        self._punched_geometry = None  # reset so that it can be re-computed

    def add_aperture(self, aperture):
        """Add an Aperture to this face.

        This method does not check the co-planarity between this Face and the
        Aperture or whether the Aperture has all vertices within the boundary of
        this Face. To check this, the Face3D.is_sub_face() method can be used
        with the Aperture and Face geometry before using this method or the
        are_sub_faces_valid() method can be used afterwards.

        Args:
            aperture: An Aperture to add to this face.
        """
        assert isinstance(aperture, Aperture), \
            'Expected Aperture. Got {}.'.format(type(aperture))
        self._acceptable_sub_face_check(Aperture)
        aperture._parent = self
        if self.normal.angle(aperture.normal) > math.pi / 2:  # reversed normal
            aperture._geometry = aperture._geometry.flip()
        self._apertures.append(aperture)
        self._punched_geometry = None  # reset so that it can be re-computed

    def add_door(self, door):
        """Add a Door to this face.

        This method does not check the co-planarity between this Face and the
        Door or whether the Door has all vertices within the boundary of
        this Face. To check this, the Face3D.is_sub_face() method can be used
        with the Door and Face geometry before using this method or the
        are_sub_faces_valid() method can be used afterwards.

        Args:
            door: A Door to add to this face.
        """
        assert isinstance(door, Door), \
            'Expected Door. Got {}.'.format(type(door))
        self._acceptable_sub_face_check(Door)
        door._parent = self
        if self.normal.angle(door.normal) > math.pi / 2:  # reversed normal
            door._geometry = door._geometry.flip()
        self._doors.append(door)
        self._punched_geometry = None  # reset so that it can be re-computed

    def add_apertures(self, apertures):
        """Add a list of Apertures to this face."""
        for aperture in apertures:
            self.add_aperture(aperture)

    def add_doors(self, doors):
        """Add a list of Doors to this face."""
        for door in doors:
            self.add_door(door)

    def set_adjacency(self, other_face, tolerance=0):
        """Set this face adjacent to another and set the other face adjacent to this one.

        Note that this method does not verify whether the other_face geometry is
        co-planar or compatible with this one so it is recommended that either the
        Face3D.is_centered_adjacent() or the Face3D.is_geometrically_equivalent()
        method be used with this face geometry and the other_face geometry
        before using this method in order to verify these criteria.

        However, this method will use the proximity of apertures and doors within
        the input tolerance to determine which of the sub faces in the other_face
        are adjacent to the ones in this face. An exception will be thrown if not
        all sub-faces can be matched.

        Args:
            other_face: Another Face object to be set adjacent to this one.
            tolerance: The minimum distance between the center of two aperture
                geometries at which they are condsidered adjacent. Default: 0.
        """
        # check the inputs and the ability of the faces to be adjacent
        assert isinstance(other_face, Face), \
            'Expected honeybee Face. Got {}.'.format(type(other_face))
        assert len(self._apertures) == len(other_face._apertures), \
            'Number of apertures does not match between {} and {}.'.format(
                self.name, other_face.name)
        assert len(self._doors) == len(other_face._doors), \
            'Number of doors does not match between {} and {}.'.format(
                self.name, other_face.name)
        # set the boundary conditions of the faces
        self._boundary_condition = Surface(other_face)
        other_face._boundary_condition = Surface(self)
        # set the apertures to be adjacent to one another
        if len(self._apertures) > 0:
            found_adjacencies = 0
            for aper_1 in self._apertures:
                for aper_2 in other_face._apertures:
                    if aper_1.center.distance_to_point(aper_2.center) <= tolerance:
                        aper_1.set_adjacency(aper_2)
                        found_adjacencies += 1
                        break
            assert len(self._apertures) == found_adjacencies, \
                'Not all apertures of {} were found to be adjacent to apertures in {}.' \
                '\nTry increasing the tolerance.'.format(self.name, other_face.name)
        # set the doors to be adjacent to one another
        if len(self._doors) > 0:
            found_adjacencies = 0
            for door_1 in self._doors:
                for door_2 in other_face._doors:
                    if door_1.center.distance_to_point(door_2.center) <= tolerance:
                        door_1.set_adjacency(door_2)
                        found_adjacencies += 1
                        break
            assert len(self._doors) == found_adjacencies, \
                'Not all doors of {} were found to be adjacent to doors in {}.' \
                '\nTry increasing the tolerance.'.format(self.name, other_face.name)

    def apertures_by_ratio(self, ratio, tolerance=0):
        """Add apertures to this Face given a ratio of aperture area to facea area.

        This method attempts to generate as few apertures as necessary to meet the ratio.
        Note that this method will remove all existing apertures and doors on this face.

        Args:
            ratio: A number between 0 and 1  (but not perfectly equal to 1)
                for the desired ratio between aperture area and face area.
            tolerance: The maximum difference between point values for them to be
                considered a part of a rectangle. This is used in the event that
                this face is concave and an attempt to subdivide the face into a
                rectangle is made. It does not affect the ability to produce apertures.

        Usage:
            room = Room.from_box(3.0, 6.0, 3.2, 180)
            room[1].apertures_by_ratio(0.4)
        """
        assert 0 <= ratio < 1, 'Ratio must be between 0 and 1. Got {}'.format(ratio)
        self._acceptable_sub_face_check(Aperture)
        self.clear_sub_faces()
        if ratio == 0:
            return
        else:
            ap_faces = self._geometry.sub_faces_by_ratio_rectangle(ratio, tolerance)
        for i, ap_face in enumerate(ap_faces):
            aperture = Aperture('{}_Glz{}'.format(self.name_original, i), ap_face)
            aperture._parent = self
            self._apertures.append(aperture)

    def apertures_by_ratio_rectangle(self, ratio, aperture_height, sill_height,
                                     horizontal_separation, vertical_separation=0,
                                     tolerance=0):
        """Add apertures to this face given a ratio of aperture area to face area.

        This function is virtually equivalent to the apertures_by_ratio method but
        any rectangular portions of this face will produce customizable rectangular
        apertures using the other inputs (aperture_height, sill_height,
        horizontal_separation, vertical_separation).

        Args:
            ratio: A number between 0 and 0.95 for the ratio between the area of
                the apertures and the area of this face.
            aperture_height: A number for the target height of the output apertures.
                Note that, if the ratio is too large for the height, the ratio will
                take precedence and the actual aperture_height will be larger
                than this value.
            sill_height: A number for the target height above the bottom edge of
                the rectangle to start the apertures. Note that, if the
                ratio is too large for the height, the ratio will take precedence
                and the sill_height will be smaller than this value.
            horizontal_separation: A number for the target separation between
                individual aperture centerlines.  If this number is larger than
                the parent rectangle base, only one aperture will be produced.
            vertical_separation: An optional number to create a single vertical
                separation between top and bottom apertures. The default is
                0 for no separation.
            tolerance: The maximum difference between point values for them to be
                considered a part of a rectangle.

        Usage:
            room = Room.from_box(3.0, 6.0, 3.2, 180)
            room[1].apertures_by_ratio_rectangle(0.4, 2, 0.9, 3)
        """
        assert 0 <= ratio <= 0.95, \
            'Ratio must be between 0 and 0.95. Got {}'.format(ratio)
        self._acceptable_sub_face_check(Aperture)
        self.clear_sub_faces()
        if ratio == 0:
            return
        else:
            ap_faces = self._geometry.sub_faces_by_ratio_sub_rectangle(
                ratio, aperture_height, sill_height, horizontal_separation,
                vertical_separation, tolerance)
        for i, ap_face in enumerate(ap_faces):
            aperture = Aperture('{}_Glz{}'.format(self.name_original, i), ap_face)
            aperture._parent = self
            self._apertures.append(aperture)

    def aperture_by_width_height(self, width, height, sill_height=1,
                                 aperture_name=None):
        """Add a single rectangular aperture to the center of this face.

        While the resulting aperture will always be in the plane of this Face,
        this method will not check to ensure that the aperture has all of its
        vertices completely within the boundary of this Face. The
        are_sub_faces_valid() method can be used afterwards to check this.

        Args:
            width: Aperture width. Aperture will be centered along.
            height: Aperture height.
            sill_height: Sill height (default: 1).
            aperture_name: Optional name for the aperture. If None, the default name
                will follow the convention "[face_name]_Glz[count]" where [count]
                is one more than the current numer of apertures in the face.

        Usage:
            room = Room.from_box(3.0, 6.0, 3.2, 180)
            room[1].aperture_by_width_height(2, 2, .7)  # aperture in front
            room[2].aperture_by_width_height(4, 1.5, .5)  # aperture on right
            room[2].aperture_by_width_height(4, 0.5, 2.2)  # aperture on right
        """
        # Perform checks
        self._acceptable_sub_face_check(Aperture)
        # Generate the aperture geometry
        face_plane = Plane(self._geometry.plane.n, self._geometry.min)
        if face_plane.y.z < 0:
            face_plane = face_plane.rotate(face_plane.n, math.pi, face_plane.o)
        center2d = face_plane.xyz_to_xy(self._geometry.center)
        x_dist = width / 2
        lower_left = Point2D(center2d.x - x_dist, sill_height)
        lower_right = Point2D(center2d.x + x_dist, sill_height)
        upper_right = Point2D(center2d.x + x_dist, sill_height + height)
        upper_left = Point2D(center2d.x - x_dist, sill_height + height)
        ap_verts2d = (lower_left, lower_right, upper_right, upper_left)
        ap_verts3d = tuple(face_plane.xy_to_xyz(pt) for pt in ap_verts2d)
        ap_face = Face3D(ap_verts3d, self._geometry.plane)
        if self.normal.angle(ap_face.normal) > math.pi / 2:  # reversed normal
            ap_face = ap_face.flip()

        # Create the aperture and add it to this Face
        name = aperture_name or '{}_Glz{}'.format(
            self.name_original, len(self.apertures))
        aperture = Aperture(name, ap_face)
        aperture._parent = self
        self._apertures.append(aperture)

    def overhang(self, depth, angle=0, indoor=False, tolerance=0):
        """Get a overhang over this entire Face.

        Args:
            depth: A number for the overhang depth.
            angle: A number for the for an angle to rotate the overhang in degrees.
                Default is 0 for no rotation.
            indoor: Boolean for whether the overhang should be generated facing the
                opposite direction of the aperture normal (typically meaning
                indoor geometry). Default: False.
            tolerance: An optional value to return None if the overhang has a length less
                than the tolerance. Default is 0, which will always yeild an overhang.

        Returns:
            overhang: A Shade object for the Face overhang. You may want to run
                the check_non_zero() method on the resulting Shade to verify
                the geometry is subtantial when the Aperture does not have a flat top.
        """
        overhang = self.louvers_by_number(
            1, depth, angle=angle, indoor=indoor, tolerance=tolerance)
        return overhang[0] if len(overhang) != 0 else None

    def louvers_by_number(self, louver_count, depth, offset=0, angle=0,
                          contour_vector=Vector3D(0, 0, 1),
                          flip_start_side=False, indoor=False, tolerance=0):
        """Get a list of louvered Shade objects over this entire Face.

        Args:
            louver_count: A positive integer for the number of louvers to generate.
            depth: A number for the depth to extrude the louvers.
            offset: A number for the distance to louvers from this Face.
                Default is 0 for no offset.
            angle: A number for the for an angle to rotate the louvers in degrees.
                Default is 0 for no rotation.
            contour_vector: A Vector3D for the direction along which contours
                are generated. Default is Z-Axis, which generates horizontal louvers.
            flip_start_side: Boolean to note whether the side the louvers start from
                should be flipped. Default is False to have louvers on top or right.
                Setting to True will start contours on the bottom or left.
            indoor: Boolean for whether louvers should be generated facing the
                opposite direction of the Face normal (typically meaning
                indoor geometry). Default: False.
            tolerance: An optional value to remove any louvers with a length less
                than the tolerance. Default is 0, which will include all louvers
                no matter how small.

        Returns:
            louvers: A list of Shade objects that cover the Face.
        """
        assert louver_count > 0, 'louver_count must be greater than 0.'
        angle = math.radians(angle)
        louvers = []
        face_geo = self.geometry if indoor is False else self.geometry.flip()
        shade_faces = face_geo.countour_fins_by_number(
            louver_count, depth, offset, angle,
            contour_vector, flip_start_side, tolerance)
        for i, shade_geo in enumerate(shade_faces):
            louvers.append(Shade('{}_Shd{}'.format(self.name_original, i), shade_geo))
        return louvers

    def louvers_by_distance_between(self, distance, depth, offset=0, angle=0,
                                    contour_vector=Vector3D(0, 0, 1),
                                    flip_start_side=False, indoor=False, tolerance=0):
        """Get a list of louvered Shade objects over this entire Face.

        Args:
            distance: A number for the approximate distance between each louver.
            depth: A number for the depth to extrude the louvers.
            offset: A number for the distance to louvers from this Face.
                Default is 0 for no offset.
            angle: A number for the for an angle to rotate the louvers in degrees.
                Default is 0 for no rotation.
            contour_vector: A Vector3D for the direction along which contours
                are generated. Default is Z-Axis, which generates horizontal louvers.
            flip_side: Boolean to note whether the side the louvers start from
                should be flipped. Default is False to have contours on top or right.
                Setting to True will start contours on the bottom or left.
            indoor: Boolean for whether louvers should be generated facing the
                opposite direction of the Face normal (typically meaning
                indoor geometry). Default: False.
            tolerance: An optional value to remove any louvers with a length less
                than the tolerance. Default is 0, which will include all louvers
                no matter how small.

        Returns:
            louvers: A list of Shade objects that cover the Face.
        """
        angle = math.radians(angle)
        louvers = []
        face_geo = self.geometry if indoor is False else self.geometry.flip()
        shade_faces = face_geo.countour_fins_by_distance_between(
            distance, depth, offset, angle, contour_vector, flip_start_side, tolerance)
        for i, shade_geo in enumerate(shade_faces):
            louvers.append(Shade('{}_Shd{}'.format(self.name_original, i), shade_geo))
        return louvers

    def move(self, moving_vec):
        """Move this Face along a vector.

        Args:
            moving_vec: A ladybug_geometry Vector3D with the direction and distance
                to move the face.
        """
        self._geometry = self.geometry.move(moving_vec)
        for ap in self._apertures:
            ap.move(moving_vec)
        for dr in self._doors:
            dr.move(moving_vec)
        self._punched_geometry = None  # reset so that it can be re-computed

    def rotate(self, axis, angle, origin):
        """Rotate this Face by a certain angle around an axis and origin.

        Args:
            axis: A ladybug_geometry Vector3D axis representing the axis of rotation.
            angle: An angle for rotation in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        ang = math.radians(angle)
        self._geometry = self.geometry.rotate(axis, ang, origin)
        for ap in self._apertures:
            ap.rotate(axis, ang, origin)
        for dr in self._doors:
            dr.rotate(axis, ang, origin)
        self._punched_geometry = None  # reset so that it can be re-computed

    def rotate_xy(self, angle, origin):
        """Rotate this Face counterclockwise in the world XY plane by a certain angle.

        Args:
            angle: An angle in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        ang = math.radians(angle)
        self._geometry = self.geometry.rotate_xy(ang, origin)
        for ap in self._apertures:
            ap.rotate_xy(ang, origin)
        for dr in self._doors:
            dr.rotate_xy(ang, origin)
        self._punched_geometry = None  # reset so that it can be re-computed

    def reflect(self, plane):
        """Reflect this Face across a plane with the input normal vector and origin.

        Args:
            plane: A ladybug_geometry Plane across which the object will
                be reflected.
        """
        assert isinstance(plane, Plane), \
            'Expected ladybug_geometry Plane. Got {}.'.format(type(plane))
        self._geometry = self.geometry.reflect(plane.n, plane.o)
        for ap in self._apertures:
            ap.reflect(plane)
        for dr in self._doors:
            dr.reflect(plane)
        self._punched_geometry = None  # reset so that it can be re-computed

    def scale(self, factor, origin=None):
        """Scale this Face by a factor from an origin point.

        Args:
            factor: A number representing how much the object should be scaled.
            origin: A ladybug_geometry Point3D representing the origin from which
                to scale. If None, it will be scaled from the World origin (0, 0, 0).
        """
        self._geometry = self.geometry.scale(factor, origin)
        for ap in self._apertures:
            ap.scale(factor, origin)
        for dr in self._doors:
            dr.scale(factor, origin)
        self._punched_geometry = None  # reset so that it can be re-computed

    def check_sub_faces_valid(self, tolerance, angle_tolerance, raise_exception=True):
        """Check that sub-faces are co-planar with this Face within the Face boundary.

        Note this does not check the planarity of the sub-faces themselves, whether
        they self-intersect, or whether they have a non-zero area.

        Args:
            tolerance: The minimum difference between the coordinate values of two
                vertices at which they can be considered equivalent.
            angle_tolerance: The max angle in degrees that the plane normals can
                differ from one another in order for them to be considered coplanar.
            raise_exception: Boolean to note whether a ValueError should be raised
                if an sub-face is not valid.
        """
        ap = self.check_apertures_valid(tolerance, angle_tolerance, raise_exception)
        dr = self.check_doors_valid(tolerance, angle_tolerance, raise_exception)
        return True if ap and dr else False

    def check_apertures_valid(self, tolerance, angle_tolerance, raise_exception=True):
        """Check that apertures are co-planar with this Face within the Face boundary.

        Note this does not check the planarity of the apertures themselves, whether
        they self-intersect, or whether they have a non-zero area.

        Args:
            tolerance: The minimum difference between the coordinate values of two
                vertices at which they can be considered equivalent.
            angle_tolerance: The max angle in degrees that the plane normals can
                differ from one another in order for them to be considered coplanar.
            raise_exception: Boolean to note whether a ValueError should be raised
                if an aperture is not valid.
        """
        for ap in self._apertures:
            if not self.geometry.is_sub_face(ap.geometry, tolerance, angle_tolerance):
                if raise_exception:
                    raise ValueError(
                        'Aperture "{}" is not coplanar or fully bounded by its parent '
                        'Face "{}".'.format(ap.name_original, self.name_original))
                return False
        return True

    def check_doors_valid(self, tolerance, angle_tolerance, raise_exception=True):
        """Check that doors are co-planar with this Face within the Face boundary.

        Note this does not check the planarity of the doors themselves, whether
        they self-intersect, or whether they have a non-zero area.

        Args:
            tolerance: The minimum difference between the coordinate values of two
                vertices at which they can be considered equivalent.
            angle_tolerance: The max angle in degrees that the plane normals can
                differ from one another in order for them to be considered coplanar.
            raise_exception: Boolean to note whether a ValueError should be raised
                if an door is not valid.
        """
        for dr in self._doors:
            if not self.geometry.is_sub_face(dr.geometry, tolerance, angle_tolerance):
                if raise_exception:
                    raise ValueError(
                        'Door "{}" is not coplanar or fully bounded by its parent '
                        'Face "{}".'.format(dr.name_original, self.name_original))
                return False
        return True

    def check_planar(self, tolerance, raise_exception=True):
        """Check whether all of the Face's vertices lie within the same plane.

        Args:
            tolerance: The minimum distance between a given vertex and a the
                object's's plane at which the vertex is said to lie in the plane.
            raise_exception: Boolean to note whether an ValueError should be
                raised if a vertex does not lie within the object's plane.
        """
        try:
            return self.geometry.validate_planarity(tolerance, raise_exception)
        except ValueError as e:
            raise ValueError('Face "{}" is not planar.\n{}'.format(
                self.name_original, e))

    def check_self_intersecting(self, raise_exception=True):
        """Check whether the edges of the Face intersect one another (like a bowtwie).

        Args:
            raise_exception: If True, a ValueError will be raised if the object
                intersects with itself. Default: True.
        """
        if self.geometry.is_self_intersecting:
            if raise_exception:
                raise ValueError('Face "{}" has self-intersecting edges.'.format(
                    self.name_original))
            return False
        return True

    def check_non_zero(self, tolerance=0.0001, raise_exception=True):
        """Check whether the area of the Face is above a certain "zero" tolerance.

        Args:
            tolerance: The minimum acceptable area of the object. Default is 0.0001,
                which is equal to 1 cm2 when model units are meters. This is just
                above the smalest size that OpenStudio will accept.
            raise_exception: If True, a ValueError will be raised if the object
                area is below the tolerance. Default: True.
        """
        if self.area < tolerance:
            if raise_exception:
                raise ValueError(
                    'Face "{}" geometry is too small. Area must be at least {}. '
                    'Got {}.'.format(self.name_original, tolerance, self.area))
            return False
        return True

    @property
    def properties(self):
        """Face properties, including Radiance, Energy and other properties."""
        return self._properties

    @property
    def to(self):
        """Face writer object.

        Use this method to access Writer class to write the face in other formats.

        Usage:
            face.to.idf(face) -> idf string.
            face.to.radiance(face) -> Radiance string.
        """
        return writer

    def to_dict(self, abridged=False, included_prop=None):
        """Return Face as a dictionary.

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
            'geometry': self._geometry.to_dict(),
            'face_type': self.type.to_dict(),
            'properties': self.properties.to_dict(abridged, included_prop)
        }
        if 'energy' in base['properties']:
            base['boundary_condition'] = self.boundary_condition.to_dict(full=True)
        else:
            base['boundary_condition'] = self.boundary_condition.to_dict(full=False)
        if self.parent:
            base['parent'] = self.parent.name
        else:
            base['parent'] = None
        if self.apertures != []:
            base['apertures'] = \
                [ap.to_dict(abridged, included_prop) for ap in self.apertures]
        if self.doors != []:
            base['doors'] = \
                [dr.to_dict(abridged, included_prop) for dr in self.doors]
        return base

    def _acceptable_sub_face_check(self, sub_face_type=Aperture):
        """Check whether the Face can accept sub-faces and raise an excption if not."""
        assert isinstance(self.boundary_condition, Outdoors), \
            '{} can only be added to Faces with a Outdoor boundary condition.'.format(
                sub_face_type.__name__)
        assert not isinstance(self.type, AirWall), \
            '{} cannot be added to AirWalls.'.format(sub_face_type.__name__)

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def ToString(self):
        return self.__repr__()

    def __copy__(self):
        new_f = Face(self.name_original, self.geometry, self.type,
                     self.boundary_condition)
        new_f._apertures = [ap.duplicate() for ap in self._apertures]
        new_f._doors = [dr.duplicate() for dr in self._doors]
        for ap in new_f._apertures:
            ap._parent = new_f
        for dr in new_f._doors:
            dr._parent = new_f
        new_f._punched_geometry = self._punched_geometry
        new_f._properties.duplicate_extension_attr(self._properties)
        return new_f

    def __repr__(self):
        return 'Face: %s' % self.name_original
