"""honeybee comparison commands."""
import sys
import logging
import json
import click

from honeybee.model import Model
from honeybee.typing import fixed_string_length
_logger = logging.getLogger(__name__)


@click.group(help='Commands for comparing Honeybee objects.')
def compare():
    pass


@compare.command('models')
@click.argument('base-model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('other-model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--include-deleted/--ignore-deleted', ' /-d', help='Flag to note whether '
    'objects that appear in the base model but not in the other model should '
    'be reported. It is useful to ignore-deleted when the other model represents '
    'only a subset of the current model.', default=True, show_default=True)
@click.option(
    '--include-added/--ignore-added', ' /-a', help='Flag to note whether '
    'whether objects that appear in the other model but not in the current '
    'model should be reported.', default=True, show_default=True)
@click.option(
    '--plain-text/--json', ' /-j', help='Flag to note whether the output validation '
    'report should be formatted as a JSON object instead of plain text. If set to JSON, '
    'the output object will contain several attributes. The "honeybee_core" and '
    '"honeybee_schema" attributes will note the versions of these libraries used in '
    'the validation process. An attribute called "fatal_error" is a text string '
    'containing an exception if the Model failed to serialize and will be an empty '
    'string if serialization was successful. An attribute called "errors" will '
    'contain a list of JSON objects for each invalid issue found in the model. A '
    'boolean attribute called "valid" will note whether the Model is valid or not.',
    default=True, show_default=True)
@click.option(
    '--output-file', '-f', help='Optional file to output the full report '
    'of differences between models. By default it will be printed out to stdout',
    type=click.File('w'), default='-')
def compare_models(
        base_model_file, other_model_file, include_deleted, include_added,
        plain_text, output_file):
    """Get a report outlining the differences between this model and another.

    The resulting report will only note top-level objects that are different
    between this model and the other. If an object has not changed at all,
    then it will not show up in the report.

    Changes to geometry are reported separately from changes in metadata
    (aka. extension properties) for each of the top level objects.

    If the Model units or tolerance are different between the two models,
    then the units and tolerance of this model will take precedence and
    the other_model will be converted to these units and tolerance for
    geometry comparison.

    \b
    Args:
        base_model: Full path to a Honeybee Model file to be used as the base
            of comparison.
        other_model: Full path to a Honeybee Model file to which the base model
            will be compared.
    """
    try:
        # re-serialize the Models
        base_model = Model.from_file(base_model_file)
        other_model = Model.from_file(other_model_file)
        ignore_deleted = not include_deleted
        ignore_added = not include_added
        # generate the comparison report
        report_dict = base_model.comparison_report(
            other_model, ignore_deleted, ignore_added)
        # write the report into a file or stdout
        if plain_text:  # convert the report into plain text
            report_text = ['COMPARISON REPORT']
            # process the changed objects into readable text
            if 'changed_objects' in report_dict and \
                    len(report_dict['changed_objects']) != 0:
                report_text.append('------------------------')
                report_text.append('CHANGED OBJECTS')
                h_txt = '  NAME                            TYPE    '
                change_keys = []
                for prop in report_dict['changed_objects'][0]:
                    if '_changed' in prop:
                        change_keys.append(prop)
                        h_txt += fixed_string_length(
                            prop.replace('_changed', '').upper(), 10)
                report_text.append(h_txt)
                for item in report_dict['changed_objects']:
                    item_txt = '  ' + fixed_string_length(item['element_name'], 30) + \
                        '  ' + fixed_string_length(item['element_type'], 10)
                    for key in change_keys:
                        if item[key]:
                            item_txt += '  X       '
                        else:
                            item_txt += '          '
                    report_text.append(item_txt)
            # process the added objects into readable text
            if 'added_objects' in report_dict and \
                    len(report_dict['added_objects']) != 0:
                report_text.append('------------------------')
                report_text.append('ADDED OBJECTS')
                h_txt = '  NAME                            TYPE    '
                for item in report_dict['added_objects']:
                    item_txt = '  ' + fixed_string_length(item['element_name'], 30) + \
                        '  ' + fixed_string_length(item['element_type'], 10)
                    report_text.append(item_txt)
            # process the deleted objects into readable text
            if 'deleted_objects' in report_dict and \
                    len(report_dict['deleted_objects']) != 0:
                report_text.append('------------------------')
                report_text.append('DELETED OBJECTS')
                h_txt = '  NAME                            TYPE    '
                for item in report_dict['deleted_objects']:
                    item_txt = '  ' + fixed_string_length(item['element_name'], 30) + \
                        '  ' + fixed_string_length(item['element_type'], 10)
                    report_text.append(item_txt)
            # write the output file
            output_file.write('\n'.join(report_text))
        else:  # just dump the dictionary to a JSON
            output_file.write(json.dumps(report_dict))
    except Exception as e:
        _logger.exception('Model comparison failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)
