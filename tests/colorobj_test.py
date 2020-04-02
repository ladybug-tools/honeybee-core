"""Test the ColorRoom and ColorFace classes."""
from honeybee.colorobj import ColorRoom, ColorFace
from honeybee.room import Room
from honeybee.face import Face
from honeybee.shade import Shade
from honeybee.aperture import Aperture
from honeybee.door import Door

from ladybug.graphic import GraphicContainer
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.plane import Plane
from ladybug_geometry.geometry3d.face import Face3D

import pytest


def test_color_room():
    """Test ColorRoom."""
    room_south = Room.from_box('SouthZone', 5, 5, 3, origin=Point3D(0, 0, 0))
    room_north = Room.from_box('NorthZone', 5, 5, 3, origin=Point3D(0, 5, 0))
    room_south[1].apertures_by_ratio(0.4, 0.01)
    room_north[3].apertures_by_ratio(0.4, 0.01)

    room_south[3].apertures_by_ratio(0.4, 0.01)
    room_south[3].apertures[0].overhang(0.5, indoor=False)
    room_south[3].apertures[0].overhang(0.5, indoor=True)
    room_south[3].apertures[0].move_shades(Vector3D(0, 0, -0.5))
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1),
                      Point3D(2.5, 10, 2.5), Point3D(4.5, 10, 2.5)]
    door = Door('FrontDoor', Face3D(door_verts))
    room_north[1].add_door(door)
    aperture = Aperture('FrontAperture', Face3D(aperture_verts))
    room_north[1].add_aperture(aperture)
    Room.solve_adjacency([room_south, room_north], 0.01)

    color_room1 = ColorRoom([room_south, room_north], 'display_name')
    color_room2 = ColorRoom([room_south, room_north], 'multiplier')
    
    assert len(color_room1.rooms) == len(color_room2.rooms) == 2
    assert color_room1.attr_name == color_room1.attr_name_end == 'display_name'
    assert color_room2.attr_name == color_room2.attr_name_end == 'multiplier'
    assert color_room1.attributes == ('SouthZone', 'NorthZone')
    assert color_room2.attributes == ('1', '1')
    assert isinstance(color_room1.graphic_container, GraphicContainer)
    assert len(color_room1.attributes_unique) == \
        len(color_room1.graphic_container.legend.segment_colors) == 2
    assert len(color_room2.attributes_unique) == \
        len(color_room2.graphic_container.legend.segment_colors) == 1
    assert len(color_room1.floor_faces) == len(color_room2.floor_faces) == 2
    assert isinstance(color_room1.min_point, Point3D)
    assert isinstance(color_room1.max_point, Point3D)


def test_color_face():
    """Test ColorFace."""
    pts_1 = [Point3D(0, 0, 0), Point3D(0, 10, 0), Point3D(10, 10, 0), Point3D(10, 0, 0)]
    pts_2 = [Point3D(0, 0, 0), Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(0, 10, 0)]
    pts_3 = [Point3D(0, 0, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(0, 0, 3)]
    pts_4 = [Point3D(10, 10, 0), Point3D(0, 10, 0), Point3D(0, 10, 3), Point3D(10, 10, 3)]
    pts_5 = [Point3D(10, 10, 0), Point3D(10, 0, 0), Point3D(10, 0, 3), Point3D(10, 10, 3)]
    pts_6 = [Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3), Point3D(0, 0, 3)]
    face_1 = Face('Face1', Face3D(pts_1))
    face_2 = Face('Face2', Face3D(pts_2))
    face_3 = Face('Face3', Face3D(pts_3))
    face_4 = Face('Face4', Face3D(pts_4))
    face_5 = Face('Face5', Face3D(pts_5))
    face_6 = Face('Face6', Face3D(pts_6))
    face_2.apertures_by_ratio(0.4, 0.01)
    face_2.apertures[0].overhang(0.5, indoor=False)
    face_2.apertures[0].overhang(0.5, indoor=True)
    face_2.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    aperture_verts = [Point3D(4.5, 5, 1), Point3D(2.5, 5, 1),
                      Point3D(2.5, 5, 2.5), Point3D(4.5, 5, 2.5)]
    door = Door('FrontDoor', Face3D(door_verts))
    aperture = Aperture('Partition', Face3D(aperture_verts))
    table_geo = Face3D.from_rectangle(2, 2, Plane(o=Point3D(1.5, 4, 1)))
    table = Shade('Table', table_geo)
    tree_canopy_geo = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(5, -3, 4)))
    tree_canopy = Shade('TreeCanopy', tree_canopy_geo)

    all_geo = [face_1, face_2, face_3, face_4, face_5, face_6, table, tree_canopy,
               aperture, door]
    color_face1 = ColorFace(all_geo, 'display_name')
    color_face2 = ColorFace(all_geo, 'boundary_condition')

    assert len(color_face1.faces) == len(color_face2.faces) == len(all_geo)
    assert len(color_face1.flat_faces) == len(color_face2.flat_faces) == len(all_geo) + 3
    assert color_face1.flat_geometry[1].has_holes  # ensure punched geometry is used
    assert color_face1.attr_name == color_face1.attr_name_end == 'display_name'
    assert color_face2.attr_name == color_face2.attr_name_end == 'boundary_condition'
    assert color_face1.attributes == \
        ('Face1', 'Face2', 'Face2_Glz0', 'Face2_Glz0_OutOverhang0',
         'Face2_Glz0_InOverhang0', 'Face3', 'Face4', 'Face5', 'Face6',
         'Table', 'TreeCanopy', 'Partition', 'FrontDoor')
    assert color_face2.attributes == \
        ('Ground', 'Outdoors', 'Outdoors', 'N/A', 'N/A', 'Outdoors', 'Outdoors',
         'Outdoors', 'Outdoors', 'N/A', 'N/A', 'Outdoors', 'Outdoors')
    assert isinstance(color_face1.graphic_container, GraphicContainer)
    assert len(color_face1.attributes_unique) == \
        len(color_face1.graphic_container.legend.segment_colors) == \
        len(color_face1.attributes)
    assert len(color_face2.attributes_unique) == \
        len(color_face2.graphic_container.legend.segment_colors) == 3
    assert isinstance(color_face1.min_point, Point3D)
    assert isinstance(color_face1.max_point, Point3D)
