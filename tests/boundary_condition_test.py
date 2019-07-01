"""test Face class."""
from honeybee.boundarycondition import boundary_conditions
from honeybee.face import Face

import pytest

bcs = boundary_conditions


def test_outdoors():
    bc = bcs.outdoors
    assert bc.name == 'Outdoors'
    assert bc.sun_exposure
    assert bc.sun_exposure_idf == 'SunExposed'
    assert bc.wind_exposure
    assert bc.wind_exposure_idf == 'WindExposed'


def test_outdoors_to_dict():
    bc = bcs.outdoors
    outdict = bc.to_dict(full=True)
    assert outdict['type'] == 'Outdoors'
    assert outdict['sun_exposure'] == 'SunExposed'
    assert outdict['wind_exposure'] == 'WindExposed'
    assert outdict['view_factor'] == 'autocalculate'
    outdict = bc.to_dict(full=False)
    assert 'sun_exposure' not in outdict
    assert 'wind_exposure' not in outdict
    assert 'view_factor' not in outdict


def test_ground():
    bc = bcs.ground
    assert bc.name == 'Ground'
    assert not bc.sun_exposure
    assert bc.sun_exposure_idf == 'NoSun'
    assert not bc.wind_exposure
    assert bc.wind_exposure_idf == 'NoWind'


def test_surface():
    vertices = [[0, 0, 0], [0, 10, 0], [0, 10, 3], [0, 0, 3]]
    face = Face.from_vertices('wall', vertices)
    bc = bcs.surface(face)
    assert bc.name == 'Surface'
    assert not bc.sun_exposure
    assert bc.sun_exposure_idf == 'NoSun'
    assert not bc.wind_exposure
    assert bc.wind_exposure_idf == 'NoWind'
    assert bc.boundary_condition_object == face.name
