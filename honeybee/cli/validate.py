"""honeybee validation commands."""

try:
    import click
except ImportError:
    raise ImportError(
        'click is not installed. Try `pip install . [cli]` command.'
    )

from honeybee.model import Model

import sys
import os
import logging
import json

_logger = logging.getLogger(__name__)

try:
    import honeybee_schema.model as schema_model
except ImportError:
    _logger.exception(
        'honeybee_schema is not installed. Try `pip install . [cli]` command.'
    )


@click.group(help='Commands for validating Honeybee JSON files.')
def validate():
    pass


@validate.command('model')
@click.argument('model-json')
def validate_model(model_json):
    """Validate all properties of a Model JSON file against the Honeybee schema.\b
    This includes basic properties like adjacency checks AND all geometry checks.
    \b
    Args:
        model_json: Full path to a Model JSON file.
    """
    try:
        # check that the file is there
        assert os.path.isfile(model_json), 'No JSON file found at {}.'.format(model_json)
        click.echo('Validating Model JSON ...')
        # first check the JSON against the OpenAPI specification
        schema_model.Model.parse_file(model_json)
        click.echo('Pydantic validation passed.')
        # re-serialize the Model to make sure no errors are found in re-serialization
        with open(model_json) as json_file:
            data = json.load(json_file)
        parsed_model = Model.from_dict(data)
        click.echo('Python re-serialization passed.')
        # perform several other checks for key honeybee model schema rules
        parsed_model.check_duplicate_room_identifiers(raise_exception=True)
        parsed_model.check_duplicate_face_identifiers(raise_exception=True)
        parsed_model.check_duplicate_sub_face_identifiers(raise_exception=True)
        parsed_model.check_duplicate_shade_identifiers(raise_exception=True)
        parsed_model.check_missing_adjacencies()
        parsed_model.check_all_air_boundaries_adjacent(raise_exception=True)
        click.echo('Unique identifier and adjacency checks passed.')
        # check that a tolerance has been specified in the model
        assert parsed_model.tolerance != 0, \
            'Model must have a non-zero tolerance in order to perform geometry checks.'
        assert parsed_model.angle_tolerance != 0, \
            'Model must have a non-zero angle_tolerance to perform geometry checks.'
        tol = parsed_model.tolerance
        ang_tol = parsed_model.angle_tolerance
        # perform several checks for key geometry rules
        parsed_model.check_non_zero(tol, raise_exception=True)
        parsed_model.check_self_intersecting(raise_exception=True)
        parsed_model.check_planar(tol, raise_exception=True)
        parsed_model.check_sub_faces_valid(tol, ang_tol, raise_exception=True)
        parsed_model.check_rooms_solid(tol, ang_tol, raise_exception=True)
        click.echo('Model geometry checks passed.')
        # if we made it to this point, report that the model is valid
        click.echo('Congratulations! Your Model JSON is valid!')
    except Exception as e:
        _logger.exception('Model validation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@validate.command('model-basic')
@click.argument('model-json')
def validate_model_basic(model_json):
    """Validate basic properties of a Model JSON against the Honeybee schema.\b
    This includes basic re-serialization, unique identifier checks, and adjacency checks.
    \b
    Args:
        model_json: Full path to a Model JSON file.
    """
    try:
        # check that the file is there
        assert os.path.isfile(model_json), 'No JSON file found at {}.'.format(model_json)
        click.echo('Validating Model JSON ...')
        # first check the JSON against the OpenAPI specification
        schema_model.Model.parse_file(model_json)
        click.echo('Pydantic validation passed.')
        # re-serialize the Model to make sure no errors are found in re-serialization
        with open(model_json) as json_file:
            data = json.load(json_file)
        parsed_model = Model.from_dict(data)
        click.echo('Python re-serialization passed.')
        # perform several other checks for key honeybee model schema rules
        parsed_model.check_duplicate_room_identifiers(raise_exception=True)
        parsed_model.check_duplicate_face_identifiers(raise_exception=True)
        parsed_model.check_duplicate_sub_face_identifiers(raise_exception=True)
        parsed_model.check_duplicate_shade_identifiers(raise_exception=True)
        parsed_model.check_missing_adjacencies()
        parsed_model.check_all_air_boundaries_adjacent(raise_exception=True)
        click.echo('Unique identifier and adjacency checks passed.')
        # if we made it to this point, report that the model is valid
        click.echo('Congratulations! The basic properties of your Model JSON are valid!')
    except Exception as e:
        _logger.exception('Model validation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@validate.command('model-geometry')
@click.argument('model-json')
def validate_model_geometry(model_json):
    """Validate geometry of a Model JSON against the Honeybee schema.\b
    This includes checks that the 5 honeybee geometry rules are upheld.
    \b
    Args:
        model_json: Full path to a Model JSON file.
    """
    try:
        # check that the file is there
        assert os.path.isfile(model_json), 'No JSON file found at {}.'.format(model_json)
        click.echo('Validating Model JSON ...')
        # re-serialize the Model to make sure no errors are found in re-serialization
        with open(model_json) as json_file:
            data = json.load(json_file)
        parsed_model = Model.from_dict(data)
        # check that a tolerance has been specified in the model
        assert parsed_model.tolerance != 0, \
            'Model must have a non-zero tolerance in order to perform geometry checks.'
        assert parsed_model.angle_tolerance != 0, \
            'Model must have a non-zero angle_tolerance to perform geometry checks.'
        tol = parsed_model.tolerance
        ang_tol = parsed_model.angle_tolerance
        # perform several checks for key geometry rules
        parsed_model.check_non_zero(tol, raise_exception=True)
        parsed_model.check_self_intersecting(raise_exception=True)
        parsed_model.check_planar(tol, raise_exception=True)
        parsed_model.check_sub_faces_valid(tol, ang_tol, raise_exception=True)
        parsed_model.check_rooms_solid(tol, ang_tol, raise_exception=True)
        # if we made it to this point, report that the model is valid
        click.echo('Congratulations! The geometry of your Model JSON is valid!')
    except Exception as e:
        _logger.exception('Model validation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)
