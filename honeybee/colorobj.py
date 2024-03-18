# coding=utf-8
"""Module for coloring geometry with attributes."""
from __future__ import division

from .shademesh import ShadeMesh
from .shade import Shade
from .door import Door
from .aperture import Aperture
from .face import Face
from .room import Room
from .facetype import Floor
from .search import get_attr_nested

from ladybug.graphic import GraphicContainer
from ladybug.legend import LegendParameters, LegendParametersCategorized
from ladybug_geometry.geometry3d.pointvector import Point3D


class _ColorObject(object):
    """Base class for visualization objects.

    Properties:
        * legend_parameters
        * attr_name
        * attr_name_end
        * attributes
        * attributes_unique
        * attributes_original
        * min_point
        * max_point
        * graphic_container
    """
    __slots__ = ('_attr_name', '_legend_parameters', '_attr_name_end',
                 '_attributes', '_attributes_unique', '_attributes_original',
                 '_min_point', '_max_point')

    def __init__(self, legend_parameters=None):
        """Initialize ColorObject."""
        # assign the legend parameters of this object
        self.legend_parameters = legend_parameters

        self._attr_name = None
        self._attr_name_end = None
        self._attributes = None
        self._attributes_unique = None
        self._attributes_original = None
        self._min_point = None
        self._max_point = None

    @property
    def legend_parameters(self):
        """Get or set the legend parameters."""
        return self._legend_parameters

    @legend_parameters.setter
    def legend_parameters(self, value):
        if value is not None:
            assert isinstance(value, LegendParameters) and not \
                isinstance(value, LegendParametersCategorized), \
                'Expected LegendParameters. Got {}.'.format(type(value))
            self._legend_parameters = value
        else:
            self._legend_parameters = LegendParameters()

    @property
    def attr_name(self):
        """Get a text string of an attribute that the input objects should have."""
        return self._attr_name

    @property
    def attr_name_end(self):
        """Get text for the last attribute in the attr_name.

        Useful when attr_name is nested.
        """
        return self._attr_name_end

    @property
    def attributes(self):
        """Get a tuple of text for the attributes assigned to the objects.

        If the input attr_name is a valid attribute for the object but None is
        assigned, the output will be 'None'. If the input attr_name is not valid
        for the input object, 'N/A' will be returned.
        """
        return self._attributes

    @property
    def attributes_unique(self):
        """Get a tuple of text for the unique attributes assigned to the objects."""
        return self._attributes_unique

    @property
    def attributes_original(self):
        """Get a tuple of objects for the attributes assigned to the objects.

        These will follow the original object typing of the attribute and won't
        be strings like the attributes.
        """
        return self._attributes_original

    @property
    def min_point(self):
        """Get a Point3D for the minimum of the box around the objects."""
        return self._min_point

    @property
    def max_point(self):
        """Get a Point3D for the maximum of the box around the objects."""
        return self._max_point

    @property
    def graphic_container(self):
        """Get a ladybug GraphicContainer that relates to this object.

        The GraphicContainer possesses almost all things needed to visualize the
        ColorRooms object including the legend, value_colors, etc.
        """
        # produce a range of values from the collected attributes
        attr_dict = {i: val for i, val in enumerate(self._attributes_unique)}
        attr_dict_rev = {val: i for i, val in attr_dict.items()}
        try:
            values = tuple(attr_dict_rev[r_attr] for r_attr in self._attributes)
        except KeyError:  # possibly caused by float cast to -0.0
            values = []
            for r_attr in self._attributes:
                if r_attr == '-0.0':
                    values.append(attr_dict_rev['0.0'])
                else:
                    values.append(attr_dict_rev[r_attr])

        # produce legend parameters with an ordinal dict for the attributes
        l_par = self.legend_parameters.duplicate()
        if l_par.is_segment_count_default:
            l_par.segment_count = len(self._attributes_unique)
        l_par.ordinal_dictionary = attr_dict
        if l_par.is_title_default:
            l_par.title = self.attr_name_end.replace('_', ' ').title()

        return GraphicContainer(values, self.min_point, self.max_point, l_par)

    def _process_attribute_name(self, attr_name):
        """Process the attribute name and assign it to this object."""
        self._attr_name = str(attr_name)
        at_split = self._attr_name.split('.')
        if len(at_split) == 1:
            self._attr_name_end = at_split[-1]
        elif at_split[-1] == 'display_name':
            self._attr_name_end = at_split[-2]
        elif at_split[-1] == '__name__' and at_split[-2] == '__class__':
            self._attr_name_end = at_split[-3]
        else:
            self._attr_name_end = at_split[-1]

    def _process_attributes(self, hb_objs):
        """Process the attributes of honeybee objects."""
        nd = self.legend_parameters.decimal_count
        attributes = [get_attr_nested(obj, self._attr_name, nd) for obj in hb_objs]
        attributes_unique = set(attributes)
        float_attr = [atr for atr in attributes_unique if isinstance(atr, float)]
        str_attr = [atr for atr in attributes_unique if isinstance(atr, str)]
        float_attr.sort()
        str_attr.sort()
        self._attributes = tuple(str(val) for val in attributes)
        self._attributes_unique = tuple(str_attr) + tuple(str(val) for val in float_attr)
        self._attributes_original = \
            tuple(get_attr_nested(obj, self._attr_name, cast_to_str=False)
                  for obj in hb_objs)

    def _calculate_min_max(self, hb_objs):
        """Calculate maximum and minimum Point3D for a set of rooms."""
        st_rm_min, st_rm_max = hb_objs[0].geometry.min, hb_objs[0].geometry.max
        min_pt = [st_rm_min.x, st_rm_min.y, st_rm_min.z]
        max_pt = [st_rm_max.x, st_rm_max.y, st_rm_max.z]

        for room in hb_objs[1:]:
            rm_min, rm_max = room.geometry.min, room.geometry.max
            if rm_min.x < min_pt[0]:
                min_pt[0] = rm_min.x
            if rm_min.y < min_pt[1]:
                min_pt[1] = rm_min.y
            if rm_min.z < min_pt[2]:
                min_pt[2] = rm_min.z
            if rm_max.x > max_pt[0]:
                max_pt[0] = rm_max.x
            if rm_max.y > max_pt[1]:
                max_pt[1] = rm_max.y
            if rm_max.z > max_pt[2]:
                max_pt[2] = rm_max.z

        self._min_point = Point3D(min_pt[0], min_pt[1], min_pt[2])
        self._max_point = Point3D(max_pt[0], max_pt[1], max_pt[2])

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()


class ColorRoom(_ColorObject):
    """Object for visualizing room-level attributes.

    Args:
        rooms: An array of honeybee Rooms, which will be colored with the attribute.
        attr_name: A text string of an attribute that the input rooms should have.
            This can have '.' that separate the nested attributes from one another.
            For example, 'properties.energy.program_type'.
        legend_parameters: An optional LegendParameter object to change the display
            of the ColorRoom (Default: None).

    Properties:
        * rooms
        * attr_name
        * legend_parameters
        * attr_name_end
        * attributes
        * attributes_unique
        * attributes_original
        * floor_faces
        * graphic_container
        * min_point
        * max_point
    """
    __slots__ = ('_rooms',)

    def __init__(self, rooms, attr_name, legend_parameters=None):
        """Initialize ColorRoom."""
        try:  # check the input rooms
            rooms = tuple(rooms)
        except TypeError:
            raise TypeError('Input rooms must be an array. Got {}.'.format(type(rooms)))
        assert len(rooms) > 0, 'ColorRooms must have at least one room.'
        for room in rooms:
            assert isinstance(room, Room), 'Expected honeybee Room for ' \
                'ColorRoom rooms. Got {}.'.format(type(room))
        self._rooms = rooms
        self._calculate_min_max(rooms)

        # assign the legend parameters of this object
        self.legend_parameters = legend_parameters

        # get the attributes of the input rooms
        self._process_attribute_name(attr_name)
        self._process_attributes(rooms)

    @property
    def rooms(self):
        """Get a tuple of honeybee Rooms assigned to this object."""
        return self._rooms

    @property
    def floor_faces(self):
        """Get a nested array with each sub-array having all floor Face3Ds of each room.

        This is useful for producing visualizations since coloring floors or rooms
        instead of the entire room solid allows more of the model to be viewed at once.
        """
        flr_faces = []
        for room in self.rooms:
            flr_faces.append(
                [face.geometry for face in room.faces if isinstance(face.type, Floor)])
        return flr_faces

    def __repr__(self):
        """Color Room representation."""
        return 'Color Room:\n{} Rooms\n{}'.format(len(self.rooms), self.attr_name_end)


class ColorFace(_ColorObject):
    """Object for visualizing face and sub-face level attributes.

    Args:
        faces: An array of honeybee Faces, Apertures, Doors, Shades and/or ShadeMeshes
            which will be colored with their attributes.
        attr_name: A text string of an attribute that the input faces should have.
            This can have '.' that separate the nested attributes from one another.
            For example, 'properties.energy.construction'.
        legend_parameters: An optional LegendParameter object to change the display
            of the ColorFace (Default: None).

    Properties:
        * faces
        * attr_name
        * legend_parameters
        * flat_faces
        * flat_geometry
        * attr_name_end
        * attributes
        * attributes_unique
        * attributes_original
        * floor_faces
        * graphic_container
        * min_point
        * max_point
    """
    __slots__ = ('_faces', '_flat_faces', '_flat_geometry')

    def __init__(self, faces, attr_name, legend_parameters=None):
        """Initialize ColorFace."""
        try:  # check the input faces
            faces = tuple(faces)
        except TypeError:
            raise TypeError('Input faces must be an array. Got {}.'.format(type(faces)))
        assert len(faces) > 0, 'ColorFaces must have at least one face.'
        flat_f = []
        for face in faces:
            if isinstance(face, Face):
                flat_f.append(face)
                flat_f.extend(face.shades)
                for ap in face.apertures:
                    flat_f.append(ap)
                    flat_f.extend(ap.shades)
                for dr in face.doors:
                    flat_f.append(dr)
                    flat_f.extend(dr.shades)
            elif isinstance(face, (Aperture, Door)):
                flat_f.append(face)
                flat_f.extend(face.shades)
            elif isinstance(face, Shade):
                flat_f.append(face)
            elif isinstance(face, ShadeMesh):
                flat_f.append(face)
            else:
                raise ValueError(
                    'Expected honeybee Face, Aperture, Door, Shade or ShadeMesh '
                    'for ColorFaces. Got {}.'.format(type(face)))
        self._faces = faces
        self._flat_faces = tuple(flat_f)
        self._flat_geometry = tuple(face.geometry if not isinstance(face, Face)
                                    else face.punched_geometry for face in flat_f)
        self._calculate_min_max(faces)

        # assign the legend parameters of this object
        self.legend_parameters = legend_parameters

        # get the attributes of the input faces
        self._process_attribute_name(attr_name)
        self._process_attributes(flat_f)

    @property
    def faces(self):
        """Get the honeybee Faces, Apertures, Doors and Shades assigned to this object.
        """
        return self._faces

    @property
    def flat_faces(self):
        """Get non-nested honeybee Faces, Apertures, Doors and Shades on this object.

        The objects here align with the attributes and graphic_container colors.
        """
        return self._flat_faces

    @property
    def flat_geometry(self):
        """Get non-nested array of faces on this object.

        The geometries here align with the attributes and graphic_container colors.
        """
        return self._flat_geometry

    def __repr__(self):
        """Color Room representation."""
        return 'Color Faces:\n{} Faces\n{}'.format(len(self.faces), self.attr_name_end)
