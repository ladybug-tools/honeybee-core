"""Test dictutil module."""
from honeybee.dictutil import dict_to_object
from honeybee.model import Model
from honeybee.room import Room
from honeybee.face import Face
from honeybee.shade import Shade
from honeybee.aperture import Aperture
from honeybee.door import Door
from honeybee.boundarycondition import Surface, Outdoors

from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.face import Face3D


import pytest


def test_dict_to_object():
    """Test the dict_to_object method with all geometry objects."""
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    north_face = room[1]
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1),
                      Point3D(2.5, 10, 2.5), Point3D(4.5, 10, 2.5)]
    door = Door('FrontDoor', Face3D(door_verts))
    north_face.add_door(door)
    aperture = Aperture('FrontAperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)
    model = Model('TinyHouse', [room])

    model_dict = model.to_dict()
    room_dict = room.to_dict()
    face_dict = south_face.to_dict()
    aperture_dict = aperture.to_dict()
    door_dict = door.to_dict()
    shade_dict = south_face.apertures[0].outdoor_shades[0].to_dict()

    assert isinstance(dict_to_object(model_dict), Model)
    assert isinstance(dict_to_object(room_dict), Room)
    assert isinstance(dict_to_object(face_dict), Face)
    assert isinstance(dict_to_object(aperture_dict), Aperture)
    assert isinstance(dict_to_object(door_dict), Door)
    assert isinstance(dict_to_object(shade_dict), Shade)


def test_dict_to_object_bc():
    """Test the dict_to_object method with boundary conditions."""
    srf = Surface(['AdjacenyFace', 'AdjacentRoom'])
    out = Outdoors()
    bc_dict = srf.to_dict()

    assert isinstance(dict_to_object(bc_dict), Surface)
