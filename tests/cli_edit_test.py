"""Test basic CLI commands that create Honeybee Models."""
import sys
import json
import pytest
from click.testing import CliRunner

from honeybee.model import Model
from honeybee.facetype import AirBoundary
from honeybee.cli.edit import convert_units, solve_adjacency, windows_by_ratio, \
    windows_by_ratio_rect, extruded_border, overhang, louvers_by_count, \
    louvers_by_distance


def test_convert_units():
    input_model = './tests/json/single_family_home.hbjson'
    runner = CliRunner()
    result = runner.invoke(convert_units, [input_model, 'Feet'])
    assert result.exit_code == 0

    model_dict = json.loads(result.output)
    new_model = Model.from_dict(model_dict)
    assert new_model.units == 'Feet'


def test_solve_adjacency():
    input_model = './tests/json/single_family_home.hbjson'
    runner = CliRunner()
    result = runner.invoke(solve_adjacency, [input_model, '-ab', '-ow'])
    assert result.exit_code == 0

    model_dict = json.loads(result.output)
    new_model = Model.from_dict(model_dict)
    ab_count = 0
    for face in new_model.faces:
        if isinstance(face.type, AirBoundary):
            ab_count += 1
    assert ab_count > 10


def test_windows_by_ratio():
    input_model = './tests/json/single_family_home.hbjson'
    runner = CliRunner()
    result = runner.invoke(windows_by_ratio, [input_model, '0.6'])
    assert result.exit_code == 0

    model_dict = json.loads(result.output)
    new_model = Model.from_dict(model_dict)
    assert new_model.exterior_aperture_area / new_model.exterior_wall_area == \
        pytest.approx(0.6, rel=1e-3)


def test_windows_by_ratio_rect():
    input_model = './tests/json/single_family_home.hbjson'
    runner = CliRunner()
    in_args = [input_model, '0.3', '2.0', '0.8', '1.0']
    result = runner.invoke(windows_by_ratio_rect, in_args)
    assert result.exit_code == 0

    model_dict = json.loads(result.output)
    new_model = Model.from_dict(model_dict)
    assert new_model.exterior_aperture_area / new_model.exterior_wall_area == \
        pytest.approx(0.3, rel=1e-3)


def test_extruded_border():
    input_model = './tests/json/single_family_home.hbjson'
    runner = CliRunner()
    in_args = [input_model, '0.2', '-i']
    result = runner.invoke(extruded_border, in_args)
    assert result.exit_code == 0

    model_dict = json.loads(result.output)
    new_model = Model.from_dict(model_dict)
    assert all(len(ap.indoor_shades) > 1 for ap in new_model.apertures)


def test_overhang():
    input_model = './tests/json/single_family_home.hbjson'
    runner = CliRunner()
    in_args = [input_model, '0.4', '-a', '10', '-vo', '0.5', '-i']
    result = runner.invoke(overhang, in_args)
    assert result.exit_code == 0

    model_dict = json.loads(result.output)
    new_model = Model.from_dict(model_dict)
    assert all(len(ap.indoor_shades) == 1 for ap in new_model.apertures)


def test_louvers_by_count():
    input_model = './tests/json/single_family_home.hbjson'
    runner = CliRunner()
    in_args = [input_model, '2', '0.2', '-a', '-10', '-o', '0.05', '-i']
    result = runner.invoke(louvers_by_count, in_args)
    assert result.exit_code == 0

    model_dict = json.loads(result.output)
    new_model = Model.from_dict(model_dict)
    assert all(len(ap.indoor_shades) == 2 for ap in new_model.apertures)


def test_louvers_by_count():
    input_model = './tests/json/single_family_home.hbjson'
    runner = CliRunner()
    in_args = [input_model, '0.25', '0.2', '-a', '-10', '-o', '0.05', '-i']
    result = runner.invoke(louvers_by_distance, in_args)
    assert result.exit_code == 0

    model_dict = json.loads(result.output)
    new_model = Model.from_dict(model_dict)
    assert all(len(ap.indoor_shades) > 2 for ap in new_model.apertures)
