"""Collection of utilities for assigning different properties based on orientation.

The functions here are meant to be adaptable to splitting up the compass based on
however many bins the user desires, though the most common arrangement is likely
to be a list of 4 values for North, East South, and West.

Usage:

.. code-block:: python

    # list of constructions + materials to apply to faces of different orientations
    ep_constructions = [constr_north, constr_east, constr_south, constr_west]
    rad_materials = [mat_north, mat_east, mat_south, mat_west]

    # check that the inputs align with one another
    all_inputs = [ep_constructions, rad_materials]
    all_inputs, num_orient = check_matching_inputs(all_inputs)

    # assign properties based on orientation
    angles = angles_from_num_orient(num_orient)
    for face in hb_faces:
        orient_i = face_orient_index(face, angles)
        if orient_i is not None:
            constr, mat = inputs_by_index(orient_i, all_inputs)
            face.properties.energy.construction = constr
            face.properties.radiance.modifier = mat
"""
from ladybug_geometry.geometry2d.pointvector import Vector2D


def angles_from_num_orient(num_subdivisions=4):
    """Get a list of angles based on the number of compass subdividsions.

    Args:
        num_subdivisions: An integer for the number of times that the compass
            should be subdivided. Default: 4, which will yield angles for North,
            East South, and West.

    Returns:
        A list of angles in degrees with a length of the num_subdivisions, which
        denote the boundaries of each orientation category.
    """
    step = 360.0 / num_subdivisions
    start = step / 2.0
    angles = []
    while start < 360:
        angles.append(start)
        start += step
    return angles


def face_orient_index(face, angles, north_vector=Vector2D(0, 1)):
    """Get the index to be used for a given face/aperture orientation from an angle list.

    Args:
        face: A honeybee Face or Aperture object.
        angles: A list of angles that denote the boundaries of each orientation
            category.
        north_vector: An optional ladybug_geometry Vector2D for the north direction.
            Default is the Y-axis (0, 1).

    Returns:
        An integer for the index used to assign properties to the object of the
        input orientation. Will be None if the input Face or Aperture is perfectly
        horizontal.
    """
    try:
        return orient_index(face.horizontal_orientation(north_vector), angles)
    except ZeroDivisionError:  # input face is perfectly horizontal
        return None


def orient_index(orientation, angles):
    """Get the index to be used for a given face/aperture orientation from an angle list.

    Args:
        orientation: The horizontal cardinal orientation of the Face or Aperture
            in degrees.
        angles: A list of angles that denote the boundaries of each orientation
            category.

    Returns:
        An integer for the index used to assign properties to the object of the
        input orientation.
    """
    for i, ang in enumerate(angles):
        if orientation < ang:
            return i
    return 0


def inputs_by_index(orientation_index, all_inputs):
    """Get all of the inputs of a certain index from a list of all_inputs.

    This is useful for getting the set of all inputs that should be assigned to
    a given Face or Aperture using its orientation_index.
    """
    return [inp[orientation_index] for inp in all_inputs]


def check_matching_inputs(all_inputs, num_orient=None):
    """Check that all orientation-specific inputs are coordinated.

    This means that each input is either a array of values to be applied to each
    orientation, which is has the same length as other orientation-specific arrays,
    or it is a single value to be used for all orientations.

    Args:
        all_inputs: An array of arrays where each sub-array corresponds to an
            orientation-specific input.
        num_orient: An optional integer for the number of orientation categories
            to be used. If None, the length of the longest input list in the
            all_inputs will be used.

    Returns:
        A tuple with two elements

        -   all_inputs -- The input all_inputs with all sub-arrays having the same length.

        -   num_orient -- An integer for the number of orientations used in the check.
    """
    num_orient = max([len(inp) for inp in all_inputs]) if num_orient is None \
        else num_orient
    for i, param_list in enumerate(all_inputs):
        if len(param_list) == 1:
            all_inputs[i] = param_list * num_orient
        else:
            assert len(param_list) == num_orient, \
                'The number of items in one of the inputs lists does not match the ' \
                'others.\nPlease ensure that either the lists match or you put in '\
                'a single value for all orientations.'
    return all_inputs, num_orient
