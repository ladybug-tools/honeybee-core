# coding=utf-8
from honeybee.config import folders

import pytest


def test_config_init():
    """Test the initialization of the config module and basic properties."""
    assert hasattr(folders, 'default_simulation_folder')
    assert folders.default_simulation_folder is None or \
        isinstance(folders.default_simulation_folder, str)
    
    assert hasattr(folders, 'python_package_path')
    assert isinstance(folders.python_package_path, str)

    assert hasattr(folders, 'python_exe_path')
    assert isinstance(folders.python_exe_path, str)
    