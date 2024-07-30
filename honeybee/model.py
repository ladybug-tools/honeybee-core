# coding: utf-8
"""Honeybee Model."""
from __future__ import division
import os
import sys
import io
import re
import json
import math
import uuid
try:  # check if we are in IronPython
    import cPickle as pickle
except ImportError:  # wea are in cPython
    import pickle

from ladybug_geometry.geometry3d import Plane, Face3D, Mesh3D
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
from .shademesh import ShadeMesh
from .typing import float_positive, invalid_dict_error, clean_string, \
    clean_and_number_string
from .config import folders
from .boundarycondition import Outdoors, Surface
from .facetype import AirBoundary, Wall, Floor, RoofCeiling, face_types
import honeybee.writer.model as writer
from honeybee.boundarycondition import boundary_conditions as bcs
try:
    ad_bc = bcs.adiabatic
except AttributeError:  # honeybee_energy is not loaded and adiabatic does not exist
    ad_bc = None


class Model(_Base):
    """A collection of Rooms, Faces, Shades, Apertures, and Doors representing a model.

    Args:
        identifier: Text string for a unique Model ID. Must be < 100 characters and
            not contain any spaces or special characters.
        rooms: A list of Room objects in the model.
        orphaned_faces: A list of the Face objects in the model that lack
            a parent Room. Note that orphaned Faces are translated to sun-blocking
            shade objects in energy simulation.
        orphaned_shades: A list of the Shade objects in the model that lack
            a parent.
        orphaned_apertures: A list of the Aperture objects in the model that lack
            a parent Face. Note that orphaned Apertures are translated to sun-blocking
            shade objects in energy simulation.
        orphaned_doors: A list of the Door objects in the model that lack
            a parent Face. Note that orphaned Doors are translated to sun-blocking
            shade objects in energy simulation.
        shade_meshes: A list of the ShadeMesh objects in the model.
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
        * shade_meshes
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
        * min
        * max
        * top_level_dict
        * user_data
    """
    __slots__ = (
        '_rooms', '_orphaned_faces', '_orphaned_apertures', '_orphaned_doors',
        '_orphaned_shades', '_shade_meshes',
        '_units', '_tolerance', '_angle_tolerance'
    )

    UNITS = UNITS
    UNITS_TOLERANCES = UNITS_TOLERANCES

    def __init__(self, identifier, rooms=None, orphaned_faces=None, orphaned_shades=None,
                 orphaned_apertures=None, orphaned_doors=None, shade_meshes=None,
                 units='Meters', tolerance=None, angle_tolerance=1.0):
        """A collection of Rooms, Faces, Apertures, and Doors for an entire model."""
        _Base.__init__(self, identifier)  # process the identifier

        self.units = units
        self.tolerance = tolerance
        self.angle_tolerance = angle_tolerance

        self._rooms = []
        self._orphaned_faces = []
        self._orphaned_apertures = []
        self._orphaned_doors = []
        self._orphaned_shades = []
        self._shade_meshes = []
        if rooms is not None:
            for room in rooms:
                self.add_room(room)
        if orphaned_faces is not None:
            for face in orphaned_faces:
                self.add_face(face)
        if orphaned_apertures is not None:
            for aperture in orphaned_apertures:
                self.add_aperture(aperture)
        if orphaned_doors is not None:
            for door in orphaned_doors:
                self.add_door(door)
        if orphaned_shades is not None:
            for shade in orphaned_shades:
                self.add_shade(shade)
        if shade_meshes is not None:
            for shade_mesh in shade_meshes:
                self.add_shade_mesh(shade_mesh)

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
        orphaned_shades = None  # import orphaned shades
        if 'orphaned_shades' in data and data['orphaned_shades'] is not None:
            orphaned_shades = []
            for s in data['orphaned_shades']:
                try:
                    orphaned_shades.append(Shade.from_dict(s))
                except Exception as e:
                    invalid_dict_error(s, e)
        shade_meshes = None  # import shade meshes
        if 'shade_meshes' in data and data['shade_meshes'] is not None:
            shade_meshes = []
            for sm in data['shade_meshes']:
                try:
                    shade_meshes.append(ShadeMesh.from_dict(sm))
                except Exception as e:
                    invalid_dict_error(sm, e)

        # build the model object
        model = Model(
            data['identifier'], rooms, orphaned_faces, orphaned_shades,
            orphaned_apertures, orphaned_doors, shade_meshes,
            units, tol, angle_tol)
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
        with io.open(hb_file, encoding='utf-8') as inf:
            first_char = inf.read(1)
            second_char = inf.read(1)
        is_json = True if first_char == '{' or second_char == '{' else False
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
        with io.open(hbjson_file, encoding='utf-8') as inf:
            inf.read(1)
            second_char = inf.read(1)
        with io.open(hbjson_file, encoding='utf-8') as inf:
            if second_char == '{':
                inf.read(1)
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
                imported as ShadeMeshes instead of Faces. (Default: False).
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
        if geometry_to_faces:
            for verts, normal in zip(stl_obj.face_vertices, stl_obj.face_normals):
                all_geo.append(Face3D(verts, plane=Plane(normal, verts[0])))
            hb_objs = [Face(all_id + '_' + str(uuid.uuid4())[:8], go) for go in all_geo]
            return Model(all_id, orphaned_faces=hb_objs, units=units,
                         tolerance=tolerance, angle_tolerance=angle_tolerance)
        else:
            mesh3d = Mesh3D.from_face_vertices(stl_obj.face_vertices)
            hb_objs = [ShadeMesh(all_id, mesh3d)]
            return Model(all_id, shade_meshes=hb_objs, units=units,
                         tolerance=tolerance, angle_tolerance=angle_tolerance)

    @classmethod
    def from_sync(cls, base_model, other_model, sync_instructions):
        """Initialize a Model from two models and instructions for syncing them.

        The SyncInstructions dictionary schema is essentially a variant of the
        ComparisonReport schema that can be obtained by calling
        base_model.comparison_report(other_model). The main difference is
        that the XXX_changed properties should be replaced with update_XXX properties
        for whether the change from the other_model should be accepted into
        the new model or rejected from it.

        Args:
            base_model: An base Honeybee Model that forms the base of
                the new model to be created.
            other_model: An other Honeybee Model that contains changes to
                the base model to be merged into the base_model.
            sync_instructions: A dictionary of SyncInstructions that states which
                changes from the other_model should be accepted or rejected
                when building a new Model from the base_model.
        """
        # make sure the unit systems of the two models align
        if base_model.units != other_model.units:
            other_model = other_model.duplicate()
            other_model.convert_to_units(base_model.units)
        # set up dictionaries of objects and lists of changes
        exist_dict = base_model.top_level_dict
        other_dict = other_model.top_level_dict
        add_dict = {
            'Room': [], 'Face': [], 'Aperture': [], 'Door': [],
            'Shade': [], 'ShadeMesh': []
        }
        del_dict = {
            'Room': [], 'Face': [], 'Aperture': [], 'Door': [],
            'Shade': [], 'ShadeMesh': []
        }
        # loop through the changed objects and record changes
        if 'changed_objects' in sync_instructions:
            for change in sync_instructions['changed_objects']:
                ex_obj = exist_dict[change['element_id']]
                up_obj = other_dict[change['element_id']]
                base_obj = up_obj if 'update_geometry' in change \
                    and change['update_geometry'] else ex_obj
                base_obj.properties._update_by_sync(
                    change, ex_obj.properties, up_obj.properties)
                del_dict[change['element_type']].append(change['element_id'])
                add_dict[change['element_type']].append(base_obj)
        # loop through deleted objects and record changes
        if 'deleted_objects' in sync_instructions:
            for change in sync_instructions['deleted_objects']:
                del_dict[change['element_type']].append(change['element_id'])
        # loop through added objects and record changes
        if 'added_objects' in sync_instructions:
            for change in sync_instructions['added_objects']:
                up_obj = other_dict[change['element_id']]
                add_dict[change['element_type']].append(up_obj)
        # duplicate the base model and make changes to it
        new_model = base_model.duplicate()
        new_model.remove_rooms(del_dict['Room'])
        new_model.remove_faces(del_dict['Face'])
        new_model.remove_apertures(del_dict['Aperture'])
        new_model.remove_doors(del_dict['Door'])
        new_model.remove_shades(del_dict['Shade'])
        new_model.remove_shade_meshes(del_dict['ShadeMesh'])
        new_model.add_rooms(add_dict['Room'])
        new_model.add_faces(add_dict['Face'])
        new_model.add_apertures(add_dict['Aperture'])
        new_model.add_doors(add_dict['Door'])
        new_model.add_shades(add_dict['Shade'])
        new_model.add_shade_meshes(add_dict['ShadeMesh'])
        return new_model

    @classmethod
    def from_sync_files(
            cls, base_model_file, other_model_file, sync_instructions_file):
        """Initialize a Model from two model files and instructions for syncing them.

        Args:
            base_model_file: An base Honeybee Model (as HBJSON or HBPkl)
                that forms the base of the new model to be created.
            other_model_file: An other Honeybee Model (as HBJSON or HBPkl)
                that contains changes to the base model to be merged into
                the base_model.
            sync_instructions: A JSON of SyncInstructions that states which
                changes from the other_model should be accepted or rejected
                when building a new Model from the base_model. The SyncInstructions
                schema is essentially a variant of the ComparisonReport schema
                that can be obtained by calling base_model.comparison_report(
                other_model). The main difference is that the XXX_changed
                properties should be replaced with update_XXX properties for
                whether the change from the other_model should be accepted into
                the new model or rejected from it.
        """
        base_model = cls.from_file(base_model_file)
        other_model = cls.from_file(other_model_file)
        assert os.path.isfile(sync_instructions_file), \
            'Failed to find %s' % sync_instructions_file
        if sys.version_info < (3, 0):
            with open(sync_instructions_file) as inf:
                sync_instructions = json.load(inf)
        else:
            with open(sync_instructions_file, encoding='utf-8') as inf:
                sync_instructions = json.load(inf)
        return cls.from_sync(base_model, other_model, sync_instructions)

    @classmethod
    def from_objects(cls, identifier, objects, units='Meters',
                     tolerance=None, angle_tolerance=1.0):
        """Initialize a Model from a list of any type of honeybee-core geometry objects.

        Args:
            identifier: Text string for a unique Model ID. Must be < 100 characters and
                not contain any spaces or special characters.
            objects: A list of honeybee Rooms, Faces, Shades, ShadeMEshes,
                Apertures and Doors.
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
        shade_meshes = []
        apertures = []
        doors = []
        for obj in objects:
            if isinstance(obj, Room):
                rooms.append(obj)
            elif isinstance(obj, Face):
                faces.append(obj)
            elif isinstance(obj, Shade):
                shades.append(obj)
            elif isinstance(obj, ShadeMesh):
                shade_meshes.append(obj)
            elif isinstance(obj, Aperture):
                apertures.append(obj)
            elif isinstance(obj, Door):
                doors.append(obj)
            else:
                raise TypeError('Expected Room, Face, Shade, Aperture or Door '
                                'for Model. Got {}'.format(type(obj)))

        return cls(identifier, rooms, faces, shades, apertures, doors, shade_meshes,
                   units, tolerance, angle_tolerance)

    @classmethod
    def from_shoe_box(
            cls, width, depth, height, orientation_angle=0, window_ratio=0,
            adiabatic=True, units='Meters', tolerance=None, angle_tolerance=1.0):
        """Create a model with a single shoe box Room.

        Args:
            width: Number for the width of the box (in the X direction).
            depth: Number for the depth of the box (in the Y direction).
            height: Number for the height of the box (in the Z direction).
            orientation_angle: A number between 0 and 360 for the clockwise
                orientation of the box in degrees. (0=North, 90=East, 180=South,
                270=West). (Default: 0).
            window_ratio: A number between 0 and 1 (but not equal to 1) for the ratio
                between aperture area and area of the face pointing towards the
                orientation-angle. Using 0 will generate no windows. (Default: 0).
            adiabatic: Boolean to note whether the faces that are not in the direction
                of the orientation-angle are adiabatic or outdoors. (Default: True)
            units: Text for the units system in which the model geometry
                exists. (Default: 'Meters').
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
        # create the box room and assign all of the attributes
        unique_id = str(uuid.uuid4())[:8]  # unique identifier for the shoe box
        tolerance = tolerance if tolerance is not None else UNITS_TOLERANCES[units]
        room_id = 'Shoe_Box_Room_{}'.format(unique_id)
        room = Room.from_box(room_id, width, depth, height, orientation_angle)
        room.display_name = 'Shoe_Box_Room'
        front_face = room[1]
        front_face.apertures_by_ratio(window_ratio, tolerance)
        if adiabatic and ad_bc:
            room[0].boundary_condition = ad_bc  # make the floor adiabatic
            for face in room[2:]:  # make all other face adiabatic
                face.boundary_condition = ad_bc
        # create the model object
        model_id = 'Shoe_Box_Model_{}'.format(unique_id)
        return cls(model_id, [room], units=units, tolerance=tolerance,
                   angle_tolerance=angle_tolerance)

    @classmethod
    def from_rectangle_plan(
            cls, width, length, floor_to_floor_height, perimeter_offset=0, story_count=1,
            orientation_angle=0, outdoor_roof=True, ground_floor=True,
            units='Meters', tolerance=None, angle_tolerance=1.0):
        """Create a model with a rectangular floor plan.

        Note that the resulting Rooms in the model won't have any windows or solved
        adjacencies. These can be added by using the Model.solve_adjacency method
        and the various Face.apertures_by_XXX methods.

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
            units: Text for the units system in which the model geometry
                exists. (Default: 'Meters').
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
        # create the honeybee rooms
        tolerance = tolerance if tolerance is not None else UNITS_TOLERANCES[units]
        unique_id = str(uuid.uuid4())[:8]  # unique identifier for the model
        rooms = Room.rooms_from_rectangle_plan(
            width, length, floor_to_floor_height, perimeter_offset, story_count,
            orientation_angle, outdoor_roof, ground_floor, unique_id, tolerance)
        # create the model object
        model_id = 'Rectangle_Plan_Model_{}'.format(unique_id)
        return cls(model_id, rooms, units=units, tolerance=tolerance,
                   angle_tolerance=angle_tolerance)

    @classmethod
    def from_l_shaped_plan(
            cls, width_1, length_1, width_2, length_2, floor_to_floor_height,
            perimeter_offset=0, story_count=1, orientation_angle=0,
            outdoor_roof=True, ground_floor=True,
            units='Meters', tolerance=None, angle_tolerance=1.0):
        """Create a model with an L-shaped floor plan.

        Note that the resulting Rooms in the model won't have any windows or solved
        adjacencies. These can be added by using the Model.solve_adjacency method
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
            units: Text for the units system in which the model geometry
                exists. (Default: 'Meters').
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
        # create the honeybee rooms
        tolerance = tolerance if tolerance is not None else UNITS_TOLERANCES[units]
        unique_id = str(uuid.uuid4())[:8]  # unique identifier for the model
        rooms = Room.rooms_from_l_shaped_plan(
            width_1, length_1, width_2, length_2, floor_to_floor_height,
            perimeter_offset, story_count,
            orientation_angle, outdoor_roof, ground_floor, unique_id, tolerance)
        # create the model object
        model_id = 'L_Shaped_Plan_Model_{}'.format(unique_id)
        return cls(model_id, rooms, units=units, tolerance=tolerance,
                   angle_tolerance=angle_tolerance)

    @property
    def units(self):
        """Get or set Text for the units system in which the model geometry exists."""
        return self._units

    @units.setter
    def units(self, value):
        value = value.title()
        assert value in UNITS, '{} is not supported as a units system. ' \
            'Choose from the following: {}'.format(value, UNITS)
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
        """Get a tuple of all Room objects in the model."""
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
    def shade_meshes(self):
        """Get a tuple of all ShadeMesh objects in the model."""
        return tuple(self._shade_meshes)

    @property
    def grouped_shades(self):
        """Get a list of lists where each sub-list contains Shades and/or ShadeMeshes
        with the same display_name.

        Assigning a common display_name to Shades and ShadeMeshes is the officially
        recommended way to group these objects for export to platforms that
        support shade groups. In this case, it is customary to use the common
        display_name as the name of the shade group.

        Note that, if no display_names have been assigned to the Shades and
        ShadeMeshes, the unique object identifier is used, meaning each sublist
        returned here should have only one item in it.
        """
        all_shades = self.shades + self._shade_meshes
        group_dict = {}
        for shade in all_shades:
            try:
                group_dict[shade.display_name].append(shade)
            except KeyError:
                group_dict[shade.display_name] = [shade]
        return list(group_dict.values())

    @property
    def orphaned_faces(self):
        """Get a tuple of all Face objects without parent Rooms in the model."""
        return tuple(self._orphaned_faces)

    @property
    def orphaned_apertures(self):
        """Get a tuple of all Aperture objects without parent Faces in the model."""
        return tuple(self._orphaned_apertures)

    @property
    def orphaned_doors(self):
        """Get a tuple of all Door objects without parent Faces in the model."""
        return tuple(self._orphaned_doors)

    @property
    def orphaned_shades(self):
        """Get a tuple of all Shade objects without parent Rooms in the model."""
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

    @property
    def top_level_dict(self):
        """Get dictionary of top-level model objects with identifiers as the keys.

        This is useful for matching these objects to others using identifiers.
        """
        base = {r.identifier: r for r in self._rooms}
        for f in self._orphaned_faces:
            base[f.identifier] = f
        for a in self._orphaned_apertures:
            base[a.identifier] = a
        for d in self._orphaned_doors:
            base[d.identifier] = d
        for s in self._orphaned_shades:
            base[s.identifier] = s
        for sm in self._shade_meshes:
            base[sm.identifier] = sm
        return base

    def add_model(self, other_model):
        """Add another Model object to this model."""
        assert isinstance(other_model, Model), \
            'Expected Model. Got {}.'.format(type(other_model))
        if self.units != other_model.units:
            other_model.convert_to_units(self.units)
        for room in other_model._rooms:
            self._rooms.append(room)
        for face in other_model._orphaned_faces:
            self._orphaned_faces.append(face)
        for shade in other_model._orphaned_shades:
            self._orphaned_shades.append(shade)
        for shade_mesh in other_model._shade_meshes:
            self._shade_meshes.append(shade_mesh)
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

    def add_shade_mesh(self, obj):
        """Add a ShadeMesh object to the model."""
        assert isinstance(obj, ShadeMesh), 'Expected ShadeMesh. Got {}.'.format(type(obj))
        self._shade_meshes.append(obj)

    def remove_rooms(self, room_ids=None):
        """Remove Rooms from the model.

        Args:
            room_ids: An optional list of Room identifiers to only remove certain rooms
                from the model. If None, all Rooms will be removed. (Default: None).
        """
        self._rooms = self._remove_by_ids(self.rooms, room_ids)

    def remove_faces(self, face_ids=None):
        """Remove orphaned Faces from the model.

        Args:
            face_ids: An optional list of Face identifiers to only remove certain faces
                from the model. If None, all Faces will be removed. (Default: None).
        """
        self._orphaned_faces = self._remove_by_ids(self._orphaned_faces, face_ids)

    def remove_apertures(self, aperture_ids=None):
        """Remove orphaned Apertures from the model.

        Args:
            aperture_ids: An optional list of Aperture identifiers to only remove
                certain apertures from the model. If None, all Apertures will
                be removed. (Default: None).
        """
        self._orphaned_apertures = self._remove_by_ids(
            self._orphaned_apertures, aperture_ids)

    def remove_doors(self, door_ids=None):
        """Remove orphaned Doors from the model.

        Args:
            door_ids: An optional list of Door identifiers to only remove certain doors
                from the model. If None, all Doors will be removed. (Default: None).
        """
        self._orphaned_doors = self._remove_by_ids(self._orphaned_doors, door_ids)

    def remove_shades(self, shade_ids=None):
        """Remove orphaned Shades from the model.

        Args:
            shade_ids: An optional list of Shade identifiers to only remove
                certain shades from the model. If None, all Shades will be
                removed. (Default: None).
        """
        self._orphaned_shades = self._remove_by_ids(self._orphaned_shades, shade_ids)

    def remove_shade_meshes(self, shade_mesh_ids=None):
        """Remove ShadeMeshes from the model.

        Args:
            shade_mesh_ids: An optional list of ShadeMesh identifiers to only remove
            certain shades from the model. If None, all Shades will be
            removed. (Default: None).
        """
        self._shade_meshes = self._remove_by_ids(self._shade_meshes, shade_mesh_ids)

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

    def add_rooms(self, objs):
        """Add a list of Room objects to the model."""
        for obj in objs:
            self.add_room(obj)

    def add_faces(self, objs):
        """Add a list of orphaned Face objects to the model."""
        for obj in objs:
            self.add_face(obj)

    def add_apertures(self, objs):
        """Add a list of orphaned Aperture objects to the model."""
        for obj in objs:
            self.add_aperture(obj)

    def add_doors(self, objs):
        """Add a list of orphaned Door objects to the model."""
        for obj in objs:
            self.add_door(obj)

    def add_shades(self, objs):
        """Add a list of orphaned Shade objects to the model."""
        for obj in objs:
            self.add_shade(obj)

    def add_shade_meshes(self, objs):
        """Add a list of ShadeMesh objects to the model."""
        for obj in objs:
            self.add_shade_mesh(obj)

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
                'The following Apertures were not found in the model:\n'
                '{}'.format(all_objs)
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

    def shade_meshes_by_identifier(self, identifiers):
        """Get a list of ShadeMesh objects in the model given the ShadeMesh identifiers.
        """
        shades, missing_ids = [], []
        model_shades = self._shade_meshes
        for obj_id in identifiers:
            for sm in model_shades:
                if sm.identifier == obj_id:
                    shades.append(sm)
                    break
            else:
                missing_ids.append(obj_id)
        if len(missing_ids) != 0:
            a_os = ' '.join(['"' + rid + '"' for rid in missing_ids])
            raise ValueError(
                'The following ShadeMeshes were not found in the model: {}'.format(a_os)
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
        for aperture in self._orphaned_apertures:
            aperture.add_prefix(prefix)
        for door in self._orphaned_doors:
            door.add_prefix(prefix)
        for shade in self._orphaned_shades:
            shade.add_prefix(prefix)
        for shade_mesh in self._shade_meshes:
            shade_mesh.add_prefix(prefix)

    def reset_ids(self, repair_surface_bcs=True):
        """Reset the identifiers of all Model objects to be derived from display_names.

        In the event that duplicate identifiers are found, an integer will be
        automatically appended to the new ID to make it unique. This is similar
        to the routines that automatically assign unique names to OpenStudio SDK objects.

        Args:
            repair_surface_bcs: A Boolean to note whether all Surface boundary
                conditions across the model should be updated with the new
                identifiers that were generated from the display names. (Default: True).
        """
        # set up dictionaries to hold various pieces of information
        room_map = self.reset_room_ids()
        face_dict, ap_dict, dr_dict, shd_dict, sm_dict = {}, {}, {}, {}, {}
        face_map, ap_map, dr_map = {}, {}, {}
        # loop through the objects and change their identifiers
        for face in self.faces:
            new_id = clean_and_number_string(
                face.display_name, face_dict, 'Face identifier')
            face_map[face.identifier] = new_id
            face.identifier = new_id
        for ap in self.apertures:
            new_id = clean_and_number_string(
                ap.display_name, ap_dict, 'Aperture identifier')
            ap_map[ap.identifier] = new_id
            ap.identifier = new_id
        for dr in self.doors:
            new_id = clean_and_number_string(
                dr.display_name, dr_dict, 'Door identifier')
            dr_map[dr.identifier] = new_id
            dr.identifier = new_id
        for shade in self.shades:
            shade.identifier = clean_and_number_string(
                shade.display_name, shd_dict, 'Shade identifier')
        for shade_mesh in self.shade_meshes:
            shade_mesh.identifier = clean_and_number_string(
                shade_mesh.display_name, sm_dict, 'ShadeMesh identifier')
        # reset all of the Surface boundary conditions if requested
        if repair_surface_bcs:
            for room in self.rooms:
                for face in room.faces:
                    if isinstance(face.boundary_condition, Surface):
                        old_objs = face.boundary_condition.boundary_condition_objects
                        try:
                            new_objs = (face_map[old_objs[0]], room_map[old_objs[1]])
                        except KeyError:  # missing adjacency
                            try:  # see if maybe the room reference is still there
                                new_objs = (old_objs[0], room_map[old_objs[1]])
                            except KeyError:  # just let the invalid adjacency pass
                                continue
                        new_bc = Surface(new_objs)
                        face.boundary_condition = new_bc
                        for ap in face.apertures:
                            old_objs = ap.boundary_condition.boundary_condition_objects
                            try:
                                new_objs = (ap_map[old_objs[0]], face_map[old_objs[1]],
                                            room_map[old_objs[2]])
                            except KeyError:  # missing adjacency
                                new_objs = (old_objs[0], old_objs[1],
                                            room_map[old_objs[2]])
                            new_bc = Surface(new_objs, True)
                            ap.boundary_condition = new_bc
                        for dr in face.doors:
                            old_objs = dr.boundary_condition.boundary_condition_objects
                            try:
                                new_objs = (dr_map[old_objs[0]], face_map[old_objs[1]],
                                            room_map[old_objs[2]])
                            except KeyError:  # missing adjacency
                                new_objs = (old_objs[0], old_objs[1],
                                            room_map[old_objs[2]])
                            new_bc = Surface(new_objs, True)
                            dr.boundary_condition = new_bc

    def reset_room_ids(self):
        """Reset the identifiers of the Model Rooms to be derived from display_names.

        In the event that duplicate Room identifiers are found, an integer will
        be automatically appended to the new Room ID to make it unique.

        Returns:
            A dictionary that relates the old identifiers (keys) to the new
            identifiers (values). This can be used to map between old and new
            objects and update things like Surface boundary conditions.
        """
        room_dict, room_map = {}, {}
        for room in self.rooms:
            new_id = clean_and_number_string(
                room.display_name, room_dict, 'Room identifier')
            room_map[room.identifier] = new_id
            room.identifier = new_id
        return room_map

    def solve_adjacency(
            self, merge_coplanar=False, intersect=False, overwrite=False,
            air_boundary=False, adiabatic=False,
            tolerance=None, angle_tolerance=None):
        """Solve adjacency between Rooms of the Model.

        Args:
            merge_coplanar: Boolean to note whether coplanar Faces of the Rooms
                should be merged before proceeding with the rest of the adjacency
                solving. This is particularly helpful when used with the intersect
                option since it will ensure the Room geometry is relatively
                clean before the intersection and adjacency solving
                occurs. (Default: False).
            intersect: Boolean to note whether the Faces of the Rooms should be
                intersected with one another before the adjacencies are
                solved. (Default: False).
            overwrite: Boolean to note whether existing Surface boundary
                conditions should be overwritten. (Default: False).
            air_boundary: Boolean to note whether the wall adjacencies should be
                of the air boundary face type. (Default: False).
            adiabatic: Boolean to note whether the adjacencies should be
                surface or adiabatic. Note that this requires honeybee-energy
                to be installed in order to have any meaning. (Default: False).
            tolerance: The maximum difference between point values for them to be
                considered equivalent. If None, the Model tolerance will be
                used. (Default: None).
            angle_tolerance: The max angle difference in degrees where Face normals
                are no longer considered coplanar. If None, the Model
                angle_tolerance will be used. (Default: None).
        """
        tol = tolerance if tolerance else self.tolerance
        ang_tol = angle_tolerance if angle_tolerance else self.angle_tolerance

        # merge coplanar faces if requested
        if merge_coplanar:
            for room in self.rooms:
                room.merge_coplanar_faces(tol, ang_tol)

        # intersect adjacencies if requested
        if intersect:
            Room.intersect_adjacency(self.rooms, tol, ang_tol)

        # solve adjacency
        if not overwrite:  # only assign new adjacencies
            adj_info = Room.solve_adjacency(self.rooms, tol)
        else:  # overwrite existing Surface BC
            adj_faces = Room.find_adjacency(self.rooms, tol)
            for face_pair in adj_faces:
                face_pair[0].set_adjacency(face_pair[1])
            adj_info = {'adjacent_faces': adj_faces}

        # try to assign the air boundary face type
        if air_boundary:
            for face_pair in adj_info['adjacent_faces']:
                if isinstance(face_pair[0].type, Wall):
                    face_pair[0].type = face_types.air_boundary
                    face_pair[1].type = face_types.air_boundary

        # try to assign the adiabatic boundary condition
        if adiabatic and ad_bc:
            for face_pair in adj_info['adjacent_faces']:
                face_pair[0].boundary_condition = ad_bc
                face_pair[1].boundary_condition = ad_bc

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
        for aperture in self._orphaned_apertures:
            aperture.move(moving_vec)
        for door in self._orphaned_doors:
            door.move(moving_vec)
        for shade in self._orphaned_shades:
            shade.move(moving_vec)
        for shade_mesh in self._shade_meshes:
            shade_mesh.move(moving_vec)
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
        for aperture in self._orphaned_apertures:
            aperture.rotate(axis, angle, origin)
        for door in self._orphaned_doors:
            door.rotate(axis, angle, origin)
        for shade in self._orphaned_shades:
            shade.rotate(axis, angle, origin)
        for shade_mesh in self._shade_meshes:
            shade_mesh.rotate(axis, angle, origin)
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
        for aperture in self._orphaned_apertures:
            aperture.rotate_xy(angle, origin)
        for door in self._orphaned_doors:
            door.rotate_xy(angle, origin)
        for shade in self._orphaned_shades:
            shade.rotate_xy(angle, origin)
        for shade_mesh in self._shade_meshes:
            shade_mesh.rotate_xy(angle, origin)
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
        for aperture in self._orphaned_apertures:
            aperture.reflect(plane)
        for door in self._orphaned_doors:
            door.reflect(plane)
        for shade in self._orphaned_shades:
            shade.reflect(plane)
        for shade_mesh in self._shade_meshes:
            shade_mesh.reflect(plane)
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
        for aperture in self._orphaned_apertures:
            aperture.scale(factor, origin)
        for door in self._orphaned_doors:
            door.scale(factor, origin)
        for shade in self._orphaned_shades:
            shade.scale(factor, origin)
        for shade_mesh in self._shade_meshes:
            shade_mesh.scale(factor, origin)
        self.properties.scale(factor, origin)

    def generate_exterior_face_grid(
            self, dimension, offset=0.1, face_type='Wall', punched_geometry=False):
        """Get a gridded Mesh3D offset from the exterior Faces of this Model.

        This will be None if the Model has no exterior Faces.

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
        for face in self.faces:
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
        """Get a gridded Mesh3D offset from the exterior Apertures of this Model.

        Will be None if the Model has no exterior Apertures.

        Args:
            dimension: The dimension of the grid cells as a number.
            offset: A number for how far to offset the grid from the base aperture.
                Positive numbers indicate an offset towards the exterior while
                negative numbers indicate an offset towards the interior, essentially
                modeling the value of sun on the building interior. (Default
                is 0.1, which will offset the grid to be 0.1 unit from the aperture).
            aperture_type: Text to specify the type of Aperture that will be used to
                generate grids. Window indicates Apertures in Walls. Choose from
                the following. (Default: All).

                * Window
                * Skylight
                * All
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
        for face in self.faces:
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

    def simplify_apertures(self, resolve_adjacency=True, tolerance=None):
        """Convert all Apertures in this Model to be a simple window ratio.

        This is useful for studies where faster simulation times are desired and
        the window ratio is the critical factor driving the results (as opposed
        to the detailed geometry of the window). Apertures assigned to concave
        Faces will not be simplified given that the Face.apertures_by_ratio method
        likely won't improve the cleanliness of the apertures for such cases.

        Args:
            resolve_adjacency: Boolean to note whether Room adjacencies should be
                re-solved after the Apertures have been simplified. Setting this
                to True should ensure that and interior Apertures that are
                simplified retain their Surface boundary conditions. If False,
                all interior Apertures that have been simplified will have an
                Outdoors boundary condition. (Default: True).
            tolerance: The maximum difference between point values for them to be
                considered equivalent. If None, the Model tolerance will be
                used. (Default: None).
        """
        tol = tolerance if tolerance else self.tolerance
        for room in self._rooms:
            room.simplify_apertures(tol)
        if resolve_adjacency:
            self.solve_adjacency()

    def rectangularize_apertures(
            self, subdivision_distance=None, max_separation=None, merge_all=False,
            resolve_adjacency=True, tolerance=None, angle_tolerance=None):
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
            resolve_adjacency: Boolean to note whether Room adjacencies should be
                re-solved after the Apertures have been rectangularized. Setting this
                to True should ensure that and interior Apertures that are
                rectangularized retain their Surface boundary conditions. If False,
                all interior Apertures that have been rectangularized will have an
                Outdoors boundary condition. (Default: True).
            tolerance: The maximum difference between point values for them to be
                considered equivalent. If None, the Model tolerance will be
                used. (Default: None).
            angle_tolerance: The max angle in degrees that the corners of the
                rectangle can differ from a right angle before it is not
                considered a rectangle. If None, the Model angle_tolerance will be
                used. (Default: None).
        """
        tol = tolerance if tolerance else self.tolerance
        a_tol = angle_tolerance if angle_tolerance else self.angle_tolerance
        for room in self._rooms:
            room.rectangularize_apertures(
                subdivision_distance, max_separation, merge_all, tol, a_tol)
        if resolve_adjacency:
            self.solve_adjacency()

    def wall_apertures_by_ratio(self, ratio, tolerance=None):
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
                for convex Faces. If None, the Model tolerance will be
                used. (Default: None).
        """
        tol = tolerance if tolerance else self.tolerance
        for room in self._rooms:
            room.wall_apertures_by_ratio(ratio, tol)

    def skylight_apertures_by_ratio(self, ratio, tolerance=None):
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
                for convex Faces. If None, the Model tolerance will be
                used. (Default: None).
        """
        tol = tolerance if tolerance else self.tolerance
        for room in self._rooms:
            room.skylight_apertures_by_ratio(ratio, tol)

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

    def rooms_to_orphaned(self):
        """Convert all Rooms in this Model to orphaned geometry objects.

        This is useful when the energy load balance of Rooms is not important
        and they are only significant as context shading. Note that this method
        will effectively discount any geometries with a Surface boundary condition
        or with an AirBoundary face type.
        """
        for room in self._rooms:
            for face in room._faces:
                face._parent = None
                if not isinstance(face.boundary_condition, Surface) and not \
                        isinstance(face.type, AirBoundary):
                    self._orphaned_faces.append(face)
        self._rooms = []

    def remove_degenerate_geometry(self, tolerance=None):
        """Remove any degenerate geometry from the model.

        Degenerate geometry refers to any objects that evaluate to less than 3 vertices
        when duplicate and colinear vertices are removed at the tolerance.

        Args:
            tolerance: The minimum distance between a vertex and the boundary segments
                at which point the vertex is considered distinct. If None, the
                Model's tolerance will be used. (Default: None).
        """
        tolerance = self.tolerance if tolerance is None else tolerance
        adj_dict = {}  # dictionary to track adjacent geometries
        for room in self.rooms:
            try:
                r_adj = room.clean_envelope(adj_dict, tolerance=tolerance)
                adj_dict.update(r_adj)
            except AssertionError as e:  # room removed; likely wrong units
                error = 'Failed to remove degenerate geometry for Room {}.\n{}'.format(
                    room.full_id, e)
                raise ValueError(error)
        self._remove_degenerate_faces(self._orphaned_faces, tolerance)
        self._remove_degenerate_faces(self._orphaned_apertures, tolerance)
        self._remove_degenerate_faces(self._orphaned_doors, tolerance)
        self._remove_degenerate_faces(self._orphaned_shades, tolerance)
        for sm in self._shade_meshes:
            sm.triangulate_and_remove_degenerate_faces(tolerance)

    def triangulate_non_planar_quads(self, tolerance=None):
        """Triangulate any non-planar orphaned geometry in the model.

        This method will only planarize the orphaned Faces, Apertures, Doors and
        Shades that are quadrilaterals, which usually has a minimal impact on results.
        It does not impact the Rooms at all.

        Args:
            tolerance: The minimum distance from the geometry plane at which the
                geometry is not considered planar. If None, the Model's tolerance
                will be used. (Default: None).
        """
        tolerance = self.tolerance if tolerance is None else tolerance
        self._orphaned_apertures = \
            self._triangulate_quad_faces(self._orphaned_apertures, tolerance)
        self._orphaned_doors = \
            self._triangulate_quad_faces(self._orphaned_doors, tolerance)
        self._orphaned_shades = \
            self._triangulate_quad_faces(self._orphaned_shades, tolerance)

    def comparison_report(self, other_model, ignore_deleted=False, ignore_added=False):
        """Get a dictionary outlining the differences between this model and another.

        The resulting dictionary will only report top-level objects that are different
        between this model and the other. If an object has not changed at all,
        then it will not show up in the report.

        Changes to geometry are reported separately from changes in metadata
        (aka. properties) for each of the top level objects.

        If the Model units or tolerance are different between the two models,
        then the units and tolerance of this model will take precedence and
        the other_model will be converted to these units and tolerance for
        geometry comparison.

        Args:
            other_model: A new Model to which this current model will be compared.
            ignore_deleted: A boolean to note whether objects that appear in this
                current model but not in the other model should be reported. It is
                useful to set this to True when the other model represents only a
                subset of the current model. (Default: False).
            ignore_added: A boolean to note whether objects that appear in the other
                model but not in the current model should be reported. (Default: False).

        Returns:
            A dictionary of differences between this model and the other model in
            the format below.
        """
        # make sure the unit systems of the two models align
        tol = self.tolerance
        if self.units != other_model.units:
            other_model = other_model.duplicate()
            other_model.convert_to_units(self.units)
        # set up lists and dictionaries of objects for comparison
        compare_dict = {'type': 'ComparisonReport'}
        self_dict = self.top_level_dict
        other_dict = other_model.top_level_dict
        # loop through the new objects and detect changes between them
        changed, added_objs = [], []
        for obj_id, new_obj in other_dict.items():
            try:
                exist_obj = self_dict[obj_id]
                change_dict = exist_obj._changed_dict(new_obj, tol)
                if change_dict is not None:
                    changed.append(change_dict)
            except KeyError:
                added_objs.append(new_obj)
        compare_dict['changed_objects'] = changed
        # include the added objects in the comparison dictionary
        if not ignore_added:
            added = []
            for new_obj in added_objs:
                added.append(new_obj._base_report_dict('AddedObject'))
            compare_dict['added_objects'] = added
        # include the deleted objects in the comparison dictionary
        if not ignore_deleted:
            deleted = []
            for obj_id, exist_obj in self_dict.items():
                try:
                    new_obj = other_dict[obj_id]
                except KeyError:
                    deleted.append(exist_obj._base_report_dict('DeletedObject'))
            compare_dict['deleted_objects'] = deleted
        return compare_dict

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

        # perform checks for duplicate identifiers, which might mess with other checks
        msgs.append(self.check_duplicate_room_identifiers(False, detailed))
        msgs.append(self.check_duplicate_face_identifiers(False, detailed))
        msgs.append(self.check_duplicate_sub_face_identifiers(False, detailed))
        msgs.append(self.check_duplicate_shade_identifiers(False, detailed))
        msgs.append(self.check_duplicate_shade_mesh_identifiers(False, detailed))

        # perform several checks for the Honeybee schema geometry rules
        msgs.append(self.check_planar(tol, False, detailed))
        msgs.append(self.check_self_intersecting(tol, False, detailed))
        # perform checks for degenerate rooms with a test that removes colinear vertices
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
                        'error_type': 'Degenerate Room Volume',
                        'extension_type': 'Core',
                        'element_type': 'Room',
                        'element_id': [room.identifier],
                        'element_name': [room.display_name],
                        'message': deg_msg
                    }]
                msgs.append(deg_msg)
        msgs.append(self.check_degenerate_rooms(tol, False, detailed))
        # perform geometry checks related to parent-child relationships
        msgs.append(self.check_sub_faces_valid(tol, ang_tol, False, detailed))
        msgs.append(self.check_sub_faces_overlapping(tol, False, detailed))
        msgs.append(self.check_upside_down_faces(ang_tol, False, detailed))
        msgs.append(self.check_rooms_solid(tol, ang_tol, False, detailed))

        # perform checks related to adjacency relationships
        msgs.append(self.check_room_volume_collisions(tol, False, detailed))
        msgs.append(self.check_missing_adjacencies(False, detailed))
        msgs.append(self.check_matching_adjacent_areas(tol, False, detailed))
        msgs.append(self.check_all_air_boundaries_adjacent(False, detailed))

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
            sub_faces, raise_exception, 'SubFace', detailed, '000002', 'Core',
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

    def check_duplicate_shade_mesh_identifiers(
            self, raise_exception=True, detailed=False):
        """Check that there are no duplicate ShadeMesh identifiers in the model.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if duplicate identifiers are found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        return check_duplicate_identifiers(
            self._shade_meshes, raise_exception, 'ShadeMesh', detailed, '000001', 'Core',
            'Duplicate ShadeMesh Identifier')

    def check_planar(self, tolerance=None, raise_exception=True, detailed=False):
        """Check that all of the Model's geometry components are planar.

        This includes all of the Model's Faces, Apertures, Doors and Shades.

        Args:
            tolerance: The minimum distance between a given vertex and a the
                object's plane at which the vertex is said to lie in the plane.
                If None, the Model tolerance will be used. (Default: None).
            raise_exception: Boolean to note whether an ValueError should be
                raised if a vertex does not lie within the object's plane.
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        tolerance = self.tolerance if tolerance is None else tolerance
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

    def check_self_intersecting(self, tolerance=None, raise_exception=True,
                                detailed=False):
        """Check that no edges of the Model's geometry components self-intersect.

        This includes all of the Model's Faces, Apertures, Doors and Shades.

        Args:
            tolerance: The minimum difference between the coordinate values of two
                vertices at which they can be considered equivalent. If None, the
                Model tolerance will be used. (Default: None).
            raise_exception: If True, a ValueError will be raised if an object
                intersects with itself (like a bowtie). (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        tolerance = self.tolerance if tolerance is None else tolerance
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

    def check_degenerate_rooms(
            self, tolerance=None, raise_exception=True, detailed=False):
        """Check whether there are degenerate Rooms (with zero volume) within the Model.

        Args:
            tolerance: The maximum difference between x, y, and z values
                at which face vertices are considered equivalent. If None, the
                Model tolerance will be used. (Default: None).
            raise_exception: Boolean to note whether a ValueError should be raised
                if degenerate Rooms are found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        tolerance = self.tolerance if tolerance is None else tolerance
        detailed = False if raise_exception else detailed
        msgs = []
        for room in self._rooms:
            msg = room.check_degenerate(tolerance, False, detailed)
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

    def check_sub_faces_valid(self, tolerance=None, angle_tolerance=None,
                              raise_exception=True, detailed=False):
        """Check that model's sub-faces are co-planar with faces and in their boundary.

        Note this does not check the planarity of the sub-faces themselves, whether
        they self-intersect, or whether they have a non-zero area.

        Args:
            tolerance: The minimum difference between the coordinate values of two
                vertices at which they can be considered equivalent. If None, the
                Model tolerance will be used. (Default: None).
            angle_tolerance: The max angle in degrees that the plane normals can
                differ from one another in order for them to be considered coplanar.
                If None, the Model angle_tolerance will be used. (Default: None).
            raise_exception: Boolean to note whether a ValueError should be raised
                if an sub-face is not valid. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        tolerance = self.tolerance if tolerance is None else tolerance
        angle_tolerance = self.angle_tolerance \
            if angle_tolerance is None else angle_tolerance
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

    def check_sub_faces_overlapping(
            self, tolerance=None, raise_exception=True, detailed=False):
        """Check that model's sub-faces do not overlap with one another.

        Args:
            tolerance: The minimum distance that two sub-faces must overlap in order
                for them to be considered overlapping and invalid. If None, the
                Model tolerance will be used. (Default: None).
            raise_exception: Boolean to note whether a ValueError should be raised
                if a sub-faces overlap with one another.
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        tolerance = self.tolerance if tolerance is None else tolerance
        detailed = False if raise_exception else detailed
        msgs = []
        for rm in self._rooms:
            msg = rm.check_sub_faces_overlapping(tolerance, False, detailed)
            if detailed:
                msgs.extend(msg)
            elif msg != '':
                msgs.append(msg)
        for f in self._orphaned_faces:
            msg = f.check_sub_faces_overlapping(tolerance, False, detailed)
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

    def check_upside_down_faces(
            self, angle_tolerance=None, raise_exception=True, detailed=False):
        """Check that the Model's Faces have the correct direction for the face type.

        This method will only report Floors that are pointing upwards or RoofCeilings
        that are pointed downwards. These cases are likely modeling errors and are in
        danger of having their vertices flipped by EnergyPlus, causing them to
        not see the sun.

        Args:
            angle_tolerance: The max angle in degrees that the Face normal can
                differ from up or down before it is considered a case of a downward
                pointing RoofCeiling or upward pointing Floor. If None, it
                will be the model angle tolerance. (Default: None).
            raise_exception: Boolean to note whether an ValueError should be
                raised if the Face is an an upward pointing Floor or a downward
                pointing RoofCeiling.
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        a_tol = self.angle_tolerance if angle_tolerance is None else angle_tolerance
        detailed = False if raise_exception else detailed
        msgs = []
        for rm in self._rooms:
            msg = rm.check_upside_down_faces(a_tol, False, detailed)
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

    def check_rooms_solid(self, tolerance=None, angle_tolerance=None,
                          raise_exception=True, detailed=False):
        """Check whether the Model's rooms are closed solid to within tolerances.

        Args:
            tolerance: tolerance: The maximum difference between x, y, and z values
                at which face vertices are considered equivalent. If None, the Model
                tolerance will be used. (Default: None).
            angle_tolerance: The max angle difference in degrees that vertices are
                allowed to differ from one another in order to consider them colinear.
                If None, the Model angle_tolerance will be used. (Default: None).
            raise_exception: Boolean to note whether a ValueError should be raised
                if the room geometry does not form a closed solid. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        tolerance = self.tolerance if tolerance is None else tolerance
        angle_tolerance = self.angle_tolerance \
            if angle_tolerance is None else angle_tolerance
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

    def check_room_volume_collisions(
            self, tolerance=None, raise_exception=True, detailed=False):
        """Check whether the Model's rooms collide with one another beyond the tolerance.

        Args:
            tolerance: tolerance: The maximum difference between x, y, and z values
                at which face vertices are considered equivalent. If None, the Model
                tolerance will be used. (Default: None).
            raise_exception: Boolean to note whether a ValueError should be raised
                if the room geometry does not form a closed solid. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        # set default values
        tolerance = self.tolerance if tolerance is None else tolerance
        detailed = False if raise_exception else detailed
        # group the rooms by their floor heights to enable collision checking
        if len(self.rooms) == 0:
            return [] if detailed else ''
        room_groups, _ = Room.group_by_floor_height(self.rooms, tolerance)
        # loop trough the groups and detect collisions
        msgs = []
        for rg in room_groups:
            msg = Room.check_room_volume_collisions(rg, tolerance, detailed)
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
                            if bc_obj in md:
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

    def check_matching_adjacent_areas(self, tolerance=None, raise_exception=True,
                                      detailed=False):
        """Check that all adjacent Faces have areas that match within the tolerance.

        This is required for energy simulation in order to get matching heat flow
        across adjacent Faces. Otherwise, conservation of energy is violated.
        Note that, if there are missing adjacencies in the model, the message from
        this method will simply note this fact without reporting on mis-matched areas.

        Args:
            tolerance: tolerance: The maximum difference between x, y, and z values
                at which face vertices are considered equivalent. If None, the Model
                tolerance will be used. (Default: None).
            raise_exception: Boolean to note whether a ValueError should be raised
                if invalid adjacencies are found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        tolerance = self.tolerance if tolerance is None else tolerance
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
        full_msgs, reported_items = [], set()
        for base_f, adj_f in zip(base_faces, adj_faces):
            if (base_f.identifier, adj_f.identifier) in reported_items:
                continue
            tol_area = math.sqrt(base_f.area) * tolerance
            if abs(base_f.area - adj_f.area) > tol_area:
                f_msg = 'Face "{}" with area {} is adjacent to Face "{}" with area {}.' \
                    ' This difference is greater than the tolerance of {}.'.format(
                        base_f.full_id, base_f.area, adj_f.full_id, adj_f.area, tolerance
                    )
                f_msg = self._validation_message_child(
                    f_msg, base_f, detailed, '000205',
                    error_type='Mismatched Area Adjacency')
                if detailed:
                    f_msg['element_id'].append(adj_f.identifier)
                    f_msg['element_name'].append(adj_f.display_name)
                    parents = []
                    rel_obj = adj_f
                    while getattr(rel_obj, '_parent', None) is not None:
                        rel_obj = getattr(rel_obj, '_parent')
                        par_dict = {
                            'parent_type': rel_obj.__class__.__name__,
                            'id': rel_obj.identifier,
                            'name': rel_obj.display_name
                        }
                        parents.append(par_dict)
                    f_msg['parents'].append(parents)
                full_msgs.append(f_msg)
                reported_items.add((adj_f.identifier, base_f.identifier))
            else:  # check to ensure the shapes are the same when vertices are removed
                try:
                    base_f_geo = base_f.geometry.remove_colinear_vertices(tolerance)
                    adj_f_geo = adj_f.geometry.remove_colinear_vertices(tolerance)
                except AssertionError:  # degenerate Faces to ignore
                    continue
                if len(base_f_geo) != len(adj_f_geo):
                    f_msg = 'Face "{}" is a shape with {} distinct vertices and is ' \
                        'adjacent to Face "{}", which has {} distinct vertices' \
                        ' within the model tolerance of {}.'.format(
                            base_f.full_id, len(base_f_geo),
                            adj_f.full_id, len(adj_f_geo), tolerance
                        )
                    f_msg = self._validation_message_child(
                        f_msg, base_f, detailed, '000205',
                        error_type='Mismatched Area Adjacency')
                    if detailed:
                        f_msg['element_id'].append(adj_f.identifier)
                        f_msg['element_name'].append(adj_f.display_name)
                        parents = []
                        rel_obj = adj_f
                        while getattr(rel_obj, '_parent', None) is not None:
                            rel_obj = getattr(rel_obj, '_parent')
                            par_dict = {
                                'parent_type': rel_obj.__class__.__name__,
                                'id': rel_obj.identifier,
                                'name': rel_obj.display_name
                            }
                            parents.append(par_dict)
                        f_msg['parents'].append(parents)
                    full_msgs.append(f_msg)
                    reported_items.add((adj_f.identifier, base_f.identifier))

            # ensure that adjacent sub-faces have matching areas
            if base_f.has_sub_faces:
                base_subs, adj_subs, sub_ids = [], [], []
                for sf in base_f.sub_faces:
                    if isinstance(sf.boundary_condition, Surface):
                        base_subs.append(sf)
                        sub_ids.append(sf.boundary_condition.boundary_condition_object)
                missing_sfs = False
                for obj_id in sub_ids:
                    for adj_sf in adj_f.sub_faces:
                        if adj_sf.identifier == obj_id:
                            adj_subs.append(adj_sf)
                            break
                    else:  # missing sub-face adjacencies will get reported elsewhere
                        missing_sfs = True
                if not missing_sfs:
                    for base_sf, adj_sf in zip(base_subs, adj_subs):
                        tol_area = math.sqrt(base_sf.area) * tolerance
                        if abs(base_sf.area - adj_sf.area) > tol_area:
                            f_msg = 'SubFace "{}" with area {} is adjacent to ' \
                                'SubFace "{}" with area {}. This difference is greater ' \
                                'than the tolerance of {}.'.format(
                                    base_sf.full_id, base_sf.area,
                                    adj_sf.full_id, adj_sf.area, tolerance
                                )
                            f_msg = self._validation_message_child(
                                f_msg, base_sf, detailed, '000205',
                                error_type='Mismatched Area Adjacency')
                            if detailed:
                                f_msg['element_id'].append(adj_sf.identifier)
                                f_msg['element_name'].append(adj_sf.display_name)
                                parents = []
                                rel_obj = adj_sf
                                while getattr(rel_obj, '_parent', None) is not None:
                                    rel_obj = getattr(rel_obj, '_parent')
                                    par_dict = {
                                        'parent_type': rel_obj.__class__.__name__,
                                        'id': rel_obj.identifier,
                                        'name': rel_obj.display_name
                                    }
                                    parents.append(par_dict)
                                f_msg['parents'].append(parents)
                            full_msgs.append(f_msg)
                            reported_items.add((adj_f.identifier, base_f.identifier))

        # return all of the validation error messages that were gathered
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

            -   parents_to_edit: An list of lists that parallels the triangulated_doors
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

    def _remove_degenerate_faces(self, hb_objs, tolerance):
        """Remove degenerate Faces, Apertures, Doors, or Shades from a list."""
        i_to_remove = []
        for i, face in enumerate(hb_objs):
            try:
                face.remove_colinear_vertices(tolerance)
            except ValueError:  # degenerate face found!
                i_to_remove.append(i)
        for i in reversed(i_to_remove):
            hb_objs.pop(i)

    def _triangulate_quad_faces(self, hb_objs, tolerance):
        """Triangulate quad geometries."""
        clean_objects = []
        for i, geo_obj in enumerate(hb_objs):
            geo = geo_obj.geometry
            if len(geo.vertices) == 4 and not geo.check_planar(tolerance, False):
                verts = geo.vertices
                obj_1 = geo_obj.duplicate()
                obj_1.identifier = '{}..0'.format(geo_obj.identifier)
                obj_1._geometry = Face3D((verts[0], verts[1], verts[2]))
                clean_objects.append(obj_1)
                obj_2 = geo_obj.duplicate()
                obj_2.identifier = '{}..1'.format(geo_obj.identifier)
                obj_2._geometry = Face3D((verts[2], verts[3], verts[0]))
                clean_objects.append(obj_2)
            else:
                clean_objects.append(geo_obj)
        return clean_objects

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
        if self._orphaned_apertures != []:
            base['orphaned_apertures'] = [ap.to_dict(True, included_prop, include_plane)
                                          for ap in self._orphaned_apertures]
        if self._orphaned_doors != []:
            base['orphaned_doors'] = [dr.to_dict(True, included_prop, include_plane)
                                      for dr in self._orphaned_doors]
        if self._orphaned_shades != []:
            base['orphaned_shades'] = [shd.to_dict(True, included_prop, include_plane)
                                       for shd in self._orphaned_shades]
        if self._shade_meshes != []:
            base['shade_meshes'] = [sm.to_dict(True, included_prop)
                                    for sm in self._shade_meshes]
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

        # convert any shade meshes into STL vertices
        for sm in self._shade_meshes:
            for fvs, fns in zip(sm.geometry.face_vertices, sm.geometry.face_normals):
                _face_vertices.append(fvs)
                _face_normals.append(fns)

        # write the geometry into an STL file
        stl_obj = STL(_face_vertices, _face_normals, self.identifier)
        return stl_obj.to_file(folder, file_name)

    def _all_objects(self):
        """Get a single list of all the Honeybee objects in a Model."""
        return self._rooms + self._orphaned_faces + self._orphaned_shades + \
            self._orphaned_apertures + self._orphaned_doors + self._shade_meshes

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
            parent_msg = 'with parent "{}" '.format(hb_obj._top_parent().full_id) \
                if hb_obj.has_parent else ''
            msg = '{} "{}" {}cannot reference itself in its Surface boundary ' \
                'condition.'.format(obj_type, hb_obj.full_id, parent_msg)
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
            parent_msg1 = 'with parent "{}" '.format(hb_obj._top_parent().full_id) \
                if hb_obj.has_parent else ''
            parent_msg2 = ' with parent "{}" '.format(bc_room) if len(bc_objs) > 1 else ''
            msg = '{} "{}" {}is adjacent to object "{}"{}, which has another adjacent ' \
                'object in the Model.'.format(
                    obj_type, hb_obj.full_id, parent_msg1, bc_obj, parent_msg2)
            msg = self._validation_message_child(
                msg, hb_obj, detailed, '000203',
                error_type='Object with Multiple Adjacencies')
            msgs.append(msg)
        else:
            bc_set.add(bc_obj)
        return msgs if detailed else ''.join(msgs)

    def _missing_adj_msg(self, messages, hb_obj, bc_obj,
                         obj_type='Face', bc_obj_type='Face', detailed=False):
        parent_msg = 'with parent "{}" '.format(hb_obj._top_parent().full_id) \
                if hb_obj.has_parent else ''
        msg = '{} "{}" {}has an adjacent {} that is missing from the model: ' \
            '{}'.format(obj_type, hb_obj.full_id, parent_msg, bc_obj_type, bc_obj)
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

    @staticmethod
    def _remove_by_ids(objs, obj_ids):
        """Remove items from a list using a list of object IDs."""
        if obj_ids == []:
            return objs
        new_objs = []
        if obj_ids is not None:
            obj_id_set = set(obj_ids)
            for obj in objs:
                if obj.identifier not in obj_id_set:
                    new_objs.append(obj)
        return new_objs

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
            [shade_mesh.duplicate() for shade_mesh in self._shade_meshes],
            self.units, self.tolerance, self.angle_tolerance)
        new_model._display_name = self._display_name
        new_model._user_data = None if self.user_data is None else self.user_data.copy()
        new_model._properties._duplicate_extension_attr(self._properties)
        return new_model

    def __repr__(self):
        return 'Model: %s' % self.display_name
