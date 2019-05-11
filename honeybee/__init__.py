"""Honeybee core library."""
import sys
import importlib
import pkgutil

__version__ = '0.0.1'

#  find and import honeybee plugins
#  this is a critical step to add additional functionalities to honeybee core library.
plugins = {
    name: importlib.import_module(name)
    for finder, name, ispkg
    in pkgutil.iter_modules()
    if name.startswith('honeybee_')
}

for key in plugins:
    print('Successfully imported: {}'.format(key))

# This is a variable to check if the library is a [+] library.
setattr(sys.modules[__name__], 'isplus', False)
