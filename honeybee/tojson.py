# coding: utf-8
"""Write json or hbjson from Honeybee objects"""

# Import standard python libraries
import os
import json

# import the core honeybee dependencies
from .model import Model
from .config import folders


def to_json(hb_objects, name=None, folder_path=None, indent=None, abridged=False):
    """This function write Honeybee objects to json file.

    Args:
        hb_objects (A list): Any Honeybee object to write to json
        name (A text string): Name of the json file
        folder_path (A text string): Path of the location where you want to write
            the json file. Deafult is "c:\\users\\**username**\\simulation"
        indent (An integer): An optional positive integer to set the indentation used in the
            resulting JSON file. If None or 0, the JSON will be a single line. Default to None.
        abridged (bool): Set to "True" to serialize the object in its abridged form.
            Abridged objects cannot be re-serialized back to honeybee objects
            on their own but they are used throughout honeybee to minimize
            file size and unnecessary duplication. Defaults to False.
    """

    # Name the file
    name = name if name is not None else 'unnamed'

    file_name = '{}.json'.format(name) if len(hb_objects) > 1 or not \
        isinstance(hb_objects[0], Model) else '{}.hbjson'.format(name)

    # Folder path to where the file will be saved
    folder = folder_path if folder_path is not None else folders.default_simulation_folder
    hb_file = os.path.join(folder, file_name)
    indent = indent if indent is not None else 0
    abridged = bool(abridged)

    # create the dictionary to be written to a JSON file
    if len(hb_objects) == 1:  # write a single object into a file if the length is 1
        try:
            obj_dict = hb_objects[0].to_dict(abridged=abridged)
        except TypeError:  # no abridged option
            obj_dict = hb_objects[0].to_dict()
    else:  # create a dictionary of the objects that are indexed by name
        obj_dict = {}
        for obj in hb_objects:
            try:
                obj_dict[obj.identifier] = obj.to_dict(abridged=abridged)
            except TypeError:  # no abridged option
                obj_dict[obj.identifier] = obj.to_dict()

    # write the dictionary into a file
    with open(hb_file, 'w') as fp:
        json.dump(obj_dict, fp, indent=indent)
