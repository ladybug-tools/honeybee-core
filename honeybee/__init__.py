"""Honeybee core library."""
import sys
import importlib
import pkgutil
import logging

#  find and import honeybee extensions
#  this is a critical step to add additional functionalities to honeybee core library.
extensions = {}
for finder, name, ispkg in pkgutil.iter_modules():
    if not name.startswith('honeybee_'):
        continue
    try:
        extensions[name] = importlib.import_module(name)
    except Exception:
        print(
            'Failed to import {0}!'
            ' To see full error message try `import {0}`'.format(name)
        )
