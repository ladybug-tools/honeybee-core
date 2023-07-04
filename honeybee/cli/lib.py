import click
import sys
import os
import logging
import zipfile
from datetime import datetime

from honeybee.config import folders

_logger = logging.getLogger(__name__)


@click.group(help='Commands for managing the standards library.')
def lib():
    pass


@lib.command('purge')
@click.option(
    '--standards-folder', '-s', default=None, help='A directory containing sub-folders '
    'of resource objects to be purged of files. If unspecified, the default user '
    'standards folder will be used.', type=click.Path(
        exists=True, file_okay=False, dir_okay=True, resolve_path=True)
)
@click.option(
    '--backup/--no-backup', ' /-xb', help='Flag to note whether a backup .zip file '
    'of the user standards library should be made before the purging operation. '
    'This is done by default in case the user ever wants to recover their old '
    'standards but can be turned off if a backup is not desired.',
    default=True, show_default=True
)
@click.option(
    '--log-file', '-log', help='Optional file to output a log of the purging process. '
    'By default this will be printed out to stdout',
    type=click.File('w'), default='-', show_default=True
)
def purge_lib(standards_folder, backup, log_file):
    """Purge the library of all user standards that it contains.

    This is useful when a user's standard library has become filled with duplicated
    objects or the user wishes to start fresh by re-exporting updated objects.
    """
    try:
        # set the folder to the default standards_folder if unspecified
        folder = standards_folder if standards_folder is not None else \
            folders.default_standards_folder
        if folder is None:
            msg = 'No standards folder could be found. Nothing was purged.'
            log_file.write(msg)
        else:
            resources = [std for std in os.listdir(folder)
                         if os.path.isdir(os.path.join(folder, std))]
            sub_folders = [os.path.join(folder, std) for std in resources]

            # make a backup of the folder if requested
            if backup:
                r_names, s_files, s_paths = [], [], []
                for sf, r_name in zip(sub_folders, resources):
                    for s_file in os.listdir(sf):
                        s_path = os.path.join(sf, s_file)
                        if os.path.isfile(s_path):
                            r_names.append(r_name)
                            s_files.append(s_file)
                            s_paths.append(s_path)
                if len(s_paths) != 0:  # there are resources to back up
                    backup_name = '.standards_backup_{}.zip'.format(
                        str(datetime.now()).split('.')[0].replace(':', '-'))
                    backup_file = os.path.join(os.path.dirname(folder), backup_name)
                    with zipfile.ZipFile(backup_file, 'w') as zf:
                        for r_name, s_file, s_path in zip(r_names, s_files, s_paths):
                            zf.write(s_path, os.path.join(r_name, s_file))

            # loop through the sub-folders and delete the files
            rel_files = []
            for sf in sub_folders:
                for s_file in os.listdir(sf):
                    s_path = os.path.join(sf, s_file)
                    if os.path.isfile(s_path):
                        rel_files.append(s_path)
            purged_files, fail_files = [], []
            for rf in rel_files:
                try:
                    os.remove(rf)
                    purged_files.append(rf)
                except Exception:
                    fail_files.append(rf)

            # report all of the deleted files in the log file
            if len(rel_files) == 0:
                log_file.write('The standards folder is empty so no files were removed.')
            if len(purged_files) != 0:
                msg = 'The following files were removed in the purging ' \
                    'operations:\n{}\n'.format('  \n'.join(purged_files))
                log_file.write(msg)
            if len(fail_files) != 0:
                msg = 'The following files could not be removed in the purging ' \
                    'operations:\n{}\n'.format('  \n'.join(fail_files))
                log_file.write(msg)
    except Exception as e:
        _logger.exception('Purging user standards library failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)
