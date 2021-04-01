"""Commands to set honeybee-core configurations."""
import click
import sys
import logging
import json

from honeybee.config import folders

_logger = logging.getLogger(__name__)


@click.group(help='Commands to set honeybee-core configurations.')
def set_config():
    pass


@set_config.command('default-simulation-folder')
@click.argument('folder-path', required=False, type=click.Path(
    exists=True, file_okay=False, dir_okay=True, resolve_path=True))
def default_simulation_folder(folder_path):
    """Set the default-simulation-folder configuration variable.

    \b
    Args:
        folder_path: Path to a folder to be set as the default-simulation-folder.
            If unspecified, the default-simulation-folder will be set back to
            the default.
    """
    try:
        config_file = folders.config_file
        with open(config_file) as inf:
            data = json.load(inf)
        data['default_simulation_folder'] = folder_path if folder_path is not None else ''
        with open(config_file, 'w') as fp:
            json.dump(data, fp, indent=4)
        msg_end = 'reset to default' if folder_path is None \
            else 'set to: {}'.format(folder_path)
        print('default-simulation-folder successfully {}.'.format(msg_end))
    except Exception as e:
        _logger.exception('Failed to set default-simulation-folder.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)
