"""test Face class."""
from honeybee.boundarycondition import boundary_conditions
from honeybee.room import Room

import pytest

bcs = boundary_conditions


def test_outdoors():
    bc = bcs.outdoors
    assert bc.name == 'Outdoors'
    assert bc.sun_exposure
    assert bc.sun_exposure_idf == 'SunExposed'
    assert bc.wind_exposure
    assert bc.wind_exposure_idf == 'WindExposed'
    assert bc.view_factor == 'autocalculate'


def test_outdoors_to_dict():
    bc = bcs.outdoors
    outdict = bc.to_dict(full=True)
    assert outdict['type'] == 'Outdoors'
    assert outdict['sun_exposure']
    assert outdict['wind_exposure']
    assert outdict['view_factor'] == 'autocalculate'
    outdict = bc.to_dict(full=False)
    assert 'sun_exposure' not in outdict
    assert 'wind_exposure' not in outdict
    assert 'view_factor' not in outdict


def test_ground():
    bc = bcs.ground
    assert bc.name == 'Ground'
    assert bc.sun_exposure_idf == 'NoSun'
    assert bc.wind_exposure_idf == 'NoWind'


def test_surface():
    room = Room.from_box('TestZone', 5, 10, 3)
    bc = bcs.surface(room[1])
    assert bc.name == 'Surface'
    assert bc.sun_exposure_idf == 'NoSun'
    assert bc.wind_exposure_idf == 'NoWind'
    assert bc.boundary_condition_object == room[1].name
