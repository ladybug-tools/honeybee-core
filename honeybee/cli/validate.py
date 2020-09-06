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
    """Validate a Model JSON file against the Honeybee schema.
    \b
    Args:
        model_json: Full path to a Model JSON file.
    """
    try:
        # check that the file is there
        assert os.path.isfile(model_json), 'No JSON file found at {}.'.format(model_json)

        # validate the Model JSON
        click.echo('Validating Model JSON ...')
        # first check the JSON against the OpenAPI specification
        schema_model.Model.parse_file(model_json)
        click.echo('Pydantic validation passed.')
        # re-serialize the Model to make sure no errors are found in re-serialization
        with open(model_json) as json_file:
            data = json.load(json_file)
        parsed_model = Model.from_dict(data)
        # perform several other checks for key honeybee model schema rules
        parsed_model.check_duplicate_room_identifiers(raise_exception=True)
        parsed_model.check_duplicate_face_identifiers(raise_exception=True)
        parsed_model.check_duplicate_sub_face_identifiers(raise_exception=True)
        parsed_model.check_duplicate_shade_identifiers(raise_exception=True)
        parsed_model.check_missing_adjacencies()
        parsed_model.check_all_air_boundaries_adjacent(raise_exception=True)
        # if we made it to this point, report that the model is valid
        click.echo('Python re-serialization passed.')
        click.echo('Congratulations! Your Model JSON is valid!')
    except Exception as e:
        _logger.exception('Model validation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)
