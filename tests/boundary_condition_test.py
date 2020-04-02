"""test Face class."""
from honeybee.boundarycondition import boundary_conditions, Outdoors, Surface, Ground
from honeybee.room import Room
from honeybee.altnumber import autocalculate

import pytest

bcs = boundary_conditions


def test_outdoors_default():
    bc = bcs.outdoors
    assert bc.name == 'Outdoors'
    assert bc.sun_exposure
    assert bc.sun_exposure_idf == 'SunExposed'
    assert bc.wind_exposure
    assert bc.wind_exposure_idf == 'WindExposed'
    assert bc.view_factor == autocalculate


def test_outdoors_custom():
    bc = Outdoors(True, False, 0.5)
    assert bc.name == 'Outdoors'
    assert bc.sun_exposure
    assert bc.sun_exposure_idf == 'SunExposed'
    assert not bc.wind_exposure
    assert bc.wind_exposure_idf == 'NoWind'
    assert bc.view_factor == 0.5


def test_outdoors_to_dict():
    bc = bcs.outdoors
    outdict = bc.to_dict(full=True)
    assert outdict['type'] == 'Outdoors'
    assert outdict['sun_exposure']
    assert outdict['wind_exposure']
    assert outdict['view_factor'] == autocalculate.to_dict()
    outdict = bc.to_dict(full=False)
    assert 'sun_exposure' not in outdict
    assert 'wind_exposure' not in outdict
    assert 'view_factor' not in outdict


def test_ground_default():
    bc = bcs.ground
    assert bc.name == 'Ground'
    assert bc.sun_exposure_idf == 'NoSun'
    assert bc.wind_exposure_idf == 'NoWind'


def test_ground_to_dict():
    bc = bcs.ground
    gdict = bc.to_dict()
    assert gdict['type'] == 'Ground'


def test_surface_from_other_object():
    room = Room.from_box('TestZone', 5, 10, 3)
    bc = bcs.surface(room[1])
    assert bc.name == 'Surface'
    assert bc.sun_exposure_idf == 'NoSun'
    assert bc.wind_exposure_idf == 'NoWind'
    assert bc.boundary_condition_object == room[1].identifier


def test_surface_custom():
    ap_adj_names = ('AdjacentAperture', 'AdjacentFace', 'AdjacentRoom')
    face_adj_names = ('AdjacentFace', 'AdjacentRoom')
    ap_bc = Surface(ap_adj_names, True)
    face_bc = Surface(face_adj_names, False)
    assert ap_bc.name == face_bc.name == 'Surface'
    assert ap_bc.boundary_condition_objects == ap_adj_names
    assert face_bc.boundary_condition_objects == face_adj_names
    with pytest.raises(AssertionError):
        ap_bc = Surface(face_adj_names, True)
    with pytest.raises(AssertionError):
        face_bc = Surface(ap_adj_names, False)


def test_surface_to_dict():
    ap_adj_names = ('AdjacentAperture', 'AdjacentFace', 'AdjacentRoom')
    face_adj_names = ('AdjacentFace', 'AdjacentRoom')
    ap_bc = Surface(ap_adj_names, True)
    face_bc = Surface(face_adj_names, False)
    ap_bc_dict = ap_bc.to_dict()
    assert ap_bc_dict['type'] == 'Surface'
    assert ap_bc_dict['boundary_condition_objects'] == ap_adj_names
    face_bc_dict = face_bc.to_dict()
    assert face_bc_dict['type'] == 'Surface'
    assert face_bc_dict['boundary_condition_objects'] == face_adj_names


def test_boundary_condition_by_name():
    """Test the boundary condition by_name method."""
    assert isinstance(bcs.by_name('Outdoors'), Outdoors)
    assert isinstance(bcs.by_name('outdoors'), Outdoors)
    assert isinstance(bcs.by_name('OUTDOORS'), Outdoors)

    assert isinstance(bcs.by_name('Ground'), Ground)
    assert isinstance(bcs.by_name('ground'), Ground)
    assert isinstance(bcs.by_name('GROUND'), Ground)

    with pytest.raises(ValueError):
        bcs.by_name('Not_a_BC')
    with pytest.raises(ValueError):
        bcs.by_name('surface')
    with pytest.raises(ValueError):
        bcs.by_name('Outdoor')
