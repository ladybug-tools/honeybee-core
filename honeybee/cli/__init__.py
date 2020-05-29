"""
Command Line Interface (CLI) entry point for honeybee and honeybee extensions.

Use this file only to add command related to honeybee-core. For adding extra commands
from each extention see below.

Note:

    Do not import this module in your code directly unless you are extending the command
    line interface. For running the commands execute them from the command line or as a
    subprocess (e.g. ``subprocess.call(['honeybee', 'viz'])``)

Honeybee is using click (https://click.palletsprojects.com/en/7.x/) for creating the CLI.
You can extend the command line interface from inside each extention by following these
steps:

1. Create a ``cli.py`` file in your extension.
2. Import the ``main`` function from this ``honeybee.cli``.
3. Add your commands and command groups to main using add_command method.
4. Add ``import [your-extention].cli`` to ``__init__.py`` file to the commands are added
   to the cli when the module is loaded.

The good practice is to group all your extention commands in a command group named after
the extension. This will make the commands organized under extension namespace. For
instance commands for `honeybee-radiance` will be called like ``honeybee radiance [radiance-command]``.


.. code-block:: python

    import click
    from honeybee.cli import main

    @click.group()
    def radiance():
        pass

    # add commands to radiance group
    @radiance.command('daylight-factor')
    # ...
    def daylight_factor():
        pass


    # finally add the newly created commands to honeybee cli
    main.add_command(radiance)

    # do not forget to import this module in __init__.py otherwise it will not be added
    # to honeybee commands.

Note:

    For extension with several commands you can use a folder structure instead of a single
    file. Refer to ``honeybee-radiance`` for an example.

"""

try:
    import click
except ImportError:
    raise ImportError(
        'click module is not installed. Try `pip install honeybee-core[cli]` command.'
    )

from honeybee.cli.validate import validate

# TODO: Comment out and use for logging once we are adding commands to this file.
# import logging
# logger = logging.getLogger(__name__)


@click.group()
@click.version_option()
def main():
    pass


@main.command('viz')
def viz():
    """Check if honeybee is flying!"""
    click.echo('viiiiiiiiiiiiizzzzzzzzz!')


main.add_command(validate)


if __name__ == "__main__":
    main()
