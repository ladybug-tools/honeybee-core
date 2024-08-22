![Honeybee](https://www.ladybug.tools/assets/img/honeybee.png)

[![Build Status](https://github.com/ladybug-tools/honeybee-core/actions/workflows/ci.yaml/badge.svg)](https://github.com/ladybug-tools/honeybee-core/actions)
[![Coverage Status](https://coveralls.io/repos/github/ladybug-tools/honeybee-core/badge.svg?branch=master)](https://coveralls.io/github/ladybug-tools/honeybee-core)

[![Python 3.10](https://img.shields.io/badge/python-3.10-orange.svg)](https://www.python.org/downloads/release/python-3100/) [![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/downloads/release/python-370/) [![Python 2.7](https://img.shields.io/badge/python-2.7-green.svg)](https://www.python.org/downloads/release/python-270/) [![IronPython](https://img.shields.io/badge/ironpython-2.7-red.svg)](https://github.com/IronLanguages/ironpython2/releases/tag/ipy-2.7.8/)

# honeybee-core

Honeybee is a collection of Python libraries to create representations of buildings
following [honeybee-schema](https://github.com/ladybug-tools/honeybee-schema/wiki).

This package is the core library that provides honeybee's common functionalities.
To extend these functionalities you should install available Honeybee extensions or write
your own.

Here are a number of frequently used extensions for Honeybee:

- [honeybee-radiance](https://github.com/ladybug-tools/honeybee-radiance): Adds daylight simulation to Honeybee.
- [honeybee-energy](https://github.com/ladybug-tools/honeybee-energy): Adds Energy simulation to Honeybee.
- [honeybee-display](https://github.com/ladybug-tools/honeybee-display): Adds VTK visualization to Honeybee.


# Installation

To install the core library use:

`pip install -U honeybee-core`

To check if Honeybee command line interface is installed correctly use `honeybee viz` and you
should get a `viiiiiiiiiiiiizzzzzzzzz!` back in response! :bee:

# [API Documentation](https://www.ladybug.tools/honeybee-core/docs/)

## Local Development
1. Clone this repo locally
```console
git clone git@github.com:ladybug-tools/honeybee-core.git

# or

git clone https://github.com/ladybug-tools/honeybee-core.git
```
2. Install dependencies:
```console
cd honeybee-core
pip install -r dev-requirements.txt
pip install -r requirements.txt
```

3. Run Tests:
```console
python -m pytest ./tests
```

4. Generate Documentation:
```console
sphinx-apidoc -f -e -d 4 -o ./docs ./honeybee
sphinx-build -b html ./docs ./docs/_build/docs
```
