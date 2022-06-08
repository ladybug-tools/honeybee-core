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
import platform
import sys
import subprocess
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
        * honeybee_core_version
        * honeybee_core_version_str
        * honeybee_schema_version
        * honeybee_schema_version_str
        * python_package_path
        * python_scripts_path
        * python_exe_path
        * python_version
        * python_version_str
        * config_file
        * mute
    """

    def __init__(self, config_file=None, mute=True):
        # set the mute value
        self.mute = bool(mute)

        # load paths from the config JSON file
        self.config_file = config_file

        # set python version to only be retrieved if requested
        self._python_version = None
        self._python_version_str = None

        # search for the version of honeybee-core and honeybee-schema
        self._honeybee_core_version = self._find_honeybee_core_version()
        self._honeybee_schema_version = self._find_honeybee_schema_version()

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
    def honeybee_core_version(self):
        """Get a tuple for the installed version of honeybee-core (eg. (1, 47, 26)).

        This will be None if the version could not be sensed (it was not installed
        via pip).
        """
        return self._honeybee_core_version

    @property
    def honeybee_core_version_str(self):
        """Get a string for the installed version of honeybee-core (eg. "1.47.26").

        This will be None if the version could not be sensed.
        """
        if self._honeybee_core_version is not None:
            return '.'.join([str(item) for item in self._honeybee_core_version])
        return None

    @property
    def honeybee_schema_version(self):
        """Get a tuple for the installed version of honeybee-schema (eg. (1, 35, 0)).

        This will be None if the version could not be sensed (it was not installed
        via pip) or if no honeybee-schema installation was found next to the
        honeybee-core installation.
        """
        return self._honeybee_schema_version

    @property
    def honeybee_schema_version_str(self):
        """Get a string for the installed version of honeybee-schema (eg. "1.35.0").

        This will be None if the version could not be sensed.
        """
        if self._honeybee_schema_version is not None:
            return '.'.join([str(item) for item in self._honeybee_schema_version])
        return None

    @property
    def python_package_path(self):
        """Get the path to where this Python package is installed."""
        # check the ladybug_tools folder for a Python installation
        py_pack = None
        lb_install = lb_config.folders.ladybug_tools_folder
        if os.path.isdir(lb_install):
            if os.name == 'nt':
                py_pack = os.path.join(lb_install, 'python', 'Lib', 'site-packages')
            elif platform.system() == 'Darwin':  # on mac, python version is in path
                py_pack = os.path.join(
                    lb_install, 'python', 'lib', 'python3.7', 'site-packages')
        if py_pack is not None and os.path.isdir(py_pack):
            return py_pack
        return os.path.split(os.path.dirname(__file__))[0]  # we're on some other cPython

    @property
    def python_scripts_path(self):
        """Get the path to where Python CLI executable files are installed.

        This can be used to call command line interface (CLI) executable files
        directly (instead of using their usual entry points).
        """
        # check the ladybug_tools folder for a Python installation
        lb_install = lb_config.folders.ladybug_tools_folder
        if os.path.isdir(lb_install):
            py_scripts = os.path.join(lb_install, 'python', 'Scripts') \
                if os.name == 'nt' else \
                os.path.join(lb_install, 'python', 'bin')
            if os.path.isdir(py_scripts):
                return py_scripts
        sys_dir = os.path.dirname(sys.executable)  # assume we are on some other cPython
        return os.path.join(sys_dir, 'Scripts') if os.name == 'nt' else sys_dir

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

    @property
    def python_version(self):
        """Get a tuple for the version of python (eg. (3, 8, 2)).

        This will be None if the version could not be sensed or if no Python
        installation was found.
        """
        if self._python_version_str is None and self.python_exe_path:
            self._python_version_from_cli()
        return self._python_version

    @property
    def python_version_str(self):
        """Get text for the full version of python (eg."3.8.2").

        This will be None if the version could not be sensed or if no Python
        installation was found.
        """
        if self._python_version_str is None and self.python_exe_path:
            self._python_version_from_cli()
        return self._python_version_str

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

    def _python_version_from_cli(self):
        """Set this object's Python version by making a call to a Python command."""
        cmds = [self.python_exe_path, '--version']
        use_shell = True if os.name == 'nt' else False
        process = subprocess.Popen(cmds, stdout=subprocess.PIPE, shell=use_shell)
        stdout = process.communicate()
        base_str = str(stdout[0]).replace("b'", '').replace(r"\r\n'", '')
        self._python_version_str = base_str.split(' ')[-1]
        try:
            self._python_version = \
                tuple(int(i) for i in self._python_version_str.split('.'))
        except Exception:
            pass  # failed to parse the version into values

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
            except OSError as e:
                if e.errno != 17:  # avoid race conditions between multiple tasks
                    raise OSError('Failed to create default simulation '
                                  'folder: %s\n%s' % (sim_folder, e))
        return sim_folder

    def _find_honeybee_core_version(self):
        """Get a tuple of 3 integers for the version of honeybee_core if installed."""
        return self._find_package_version('honeybee_core')

    def _find_honeybee_schema_version(self):
        """Get a tuple of 3 integers for the version of honeybee_schema if installed."""
        return self._find_package_version('honeybee_schema')

    def _find_package_version(self, package_name):
        """Get a tuple of 3 integers for the version of a package."""
        hb_info_folder = None
        for item in os.listdir(self.python_package_path):
            if item.startswith(package_name + '-') and item.endswith('.dist-info'):
                if os.path.isdir(os.path.join(self.python_package_path, item)):
                    hb_info_folder = item
                    break
        if hb_info_folder is not None:
            hb_info_folder = hb_info_folder.replace('.dist-info', '')
            ver = ''.join(s for s in hb_info_folder if (s.isdigit() or s == '.'))
            if ver:  # version was found in the file path name
                return tuple(int(d) for d in ver.split('.'))
        return None


"""Object possesing all key folders within the configuration."""
folders = Folders()
