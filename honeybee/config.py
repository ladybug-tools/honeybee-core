"""Honeybee configurations.

Import this into every module where access configurations are needed.

Usage:

.. code-block:: python

    from honeybee.config import folders
    print(folders.python_exe_path)
    print(folders.default_simulation_folder)
    folders.default_simulation_folder = "C:/my_sim_folder"
"""
import ladybug.config as lb_config

import os
import sys
import json


class Folders(object):
    """Honeybee folders.

    Args:
        config_file: The path to the config.json file from which folders are loaded.
            If None, the config.json module included in this package will be used.
            Default: None.
        mute: If False, the paths to the various folders will be printed as they
            are found. If True, no printing will occur upon initialization of this
            class. Default: True.

    Properties:
        * default_simulation_folder
        * config_file
        * mute
        * python_package_path
        * python_exe_path
    """

    def __init__(self, config_file=None, mute=True):
        # set the mute value
        self.mute = bool(mute)

        # load paths from the config JSON file
        self.config_file = config_file

    @property
    def default_simulation_folder(self):
        """Get or set the path to the default simulation folder."""
        return self._default_simulation_folder

    @default_simulation_folder.setter
    def default_simulation_folder(self, path):
        if not path:  # check the default location for simulations
            path = self._find_default_simulation_folder()

        self._default_simulation_folder = path

        if not self.mute and self._default_simulation_folder:
            print('Path to the default simulation folder is set to: '
                  '{}'.format(self._default_simulation_folder))

    @property
    def config_file(self):
        """Get or set the path to the config.json file from which folders are loaded.

        Setting this to None will result in using the config.json module included
        in this package.
        """
        return self._config_file

    @config_file.setter
    def config_file(self, cfg):
        if cfg is None:
            cfg = os.path.join(os.path.dirname(__file__), 'config.json')
        self._load_from_file(cfg)
        self._config_file = cfg

    @property
    def python_package_path(self):
        """Get the path to where this Python package is installed."""
        return os.path.split(os.path.dirname(__file__))[0]

    @property
    def python_exe_path(self):
        """Get the path to the Python executable to be used for Ladybug Tools CLI calls.

        If a version of Python is found within the ladybug_tools installation folder,
        this will be the path to that version of Python. Otherwise, it will be
        assumed that this is package is installed in cPython outside of the ladybug_tools
        folder and the sys.executable will be returned.
        """
        # check the ladybug_tools folder for a Python installation
        lb_install = lb_config.folders.ladybug_tools_folder
        if os.path.isdir(lb_install):
            py_exe_file = os.path.join(lb_install, 'python', 'python.exe') \
                if os.name == 'nt' else \
                os.path.join(lb_install, 'python', 'bin', 'python3')
            if os.path.isfile(py_exe_file):
                return py_exe_file
        return sys.executable  # assume we are on some other cPython

    def _load_from_file(self, file_path):
        """Set all of the the properties of this object from a config JSON file.

        Args:
            file_path: Path to a JSON file containing the file paths. A sample of this
                JSON is the config.json file within this package.
        """
        # check the default file path
        assert os.path.isfile(file_path), \
            ValueError('No file found at {}'.format(file_path))

        # set the default paths to be all blank
        default_path = {
            "default_simulation_folder": r''
        }

        with open(file_path, 'r') as cfg:
            try:
                paths = json.load(cfg)
            except Exception as e:
                print('Failed to load paths from {}.\nThey will be set to defaults '
                      'instead\n{}'.format(file_path, e))
            else:
                for key, p in paths.items():
                    if not key.startswith('__') and p.strip():
                        default_path[key] = p.strip()

        # set paths for the default_simulation_folder
        self.default_simulation_folder = default_path["default_simulation_folder"]

    @staticmethod
    def _find_default_simulation_folder():
        """Find the the default simulation folder in its usual location.

        An attempt will be made to create the directory if it does not already exist.
        """
        home_folder = os.getenv('HOME') or os.path.expanduser('~')
        sim_folder = os.path.join(home_folder, 'simulation')
        if not os.path.isdir(sim_folder):
            try:
                os.makedirs(sim_folder)
            except Exception as e:
                raise OSError('Failed to create default simulation '
                              'folder: %s\n%s' % (sim_folder, e))
        return sim_folder


"""Object possesing all key folders within the configuration."""
folders = Folders()
