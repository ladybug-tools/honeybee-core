"""Honeybee core library."""
import sys
import importlib
import pkgutil


#  find and import honeybee extensions
#  this is a critical step to add additional functionalities to honeybee core library.
extensions = {
    name: importlib.import_module(name)
    for finder, name, ispkg
    in pkgutil.iter_modules()
    if name.startswith('honeybee_')
}

for key in extensions:
    print('Successfully imported: {}'.format(key))

# This is a variable to check if the library is a [+] library.
setattr(sys.modules[__name__], 'isplus', False)
