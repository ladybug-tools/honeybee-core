
Welcome to Honeybee's documentation!
=========================================

.. image:: http://www.ladybug.tools/assets/img/honeybee.png

Honeybee is a collection of Python libraries to create representations of buildings
following `honeybee-schema <https://github.com/ladybug-tools/honeybee-schema/wiki>`_.

This package is the core library that provides honeybee's common functionalities.
To extend these functionalities you should install available Honeybee extensions or write
your own.

Installation
============

To install the core library try ``pip install -U honeybee-core``.

To check if the Honeybee command line interface is installed correctly try ``honeybee viz`` and you
should get a ``viiiiiiiiiiiiizzzzzzzzz!`` back in response!


Documentation
=============

This document includes `Honeybee API documentation <#honeybee>`_ and 
`Honeybee Command Line Interface <#id1>`_ documentation for ``honeybee core`` and does
not include the documentation for honeybee extensions. For each extension refer to
extension's documentation page.

Here are a number of Honeybee popular extensions:

- `honeybee-energy <https://ladybug.tools/honeybee-energy/docs>`_
- `honeybee-radiance <https://ladybug.tools/honeybee-radiance/docs>`_


.. toctree::
   :maxdepth: 2
   :caption: Contents:

.. include:: modules.rst
.. include:: cli.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
