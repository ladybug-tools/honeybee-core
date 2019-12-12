from honeybee.orientation import angles_from_num_orient, face_orient_index, \
    inputs_by_index, check_matching_inputs
from honeybee.boundarycondition import boundary_conditions, Outdoors, Ground
from honeybee.room import Room

from ladybug_geometry.geometry3d.pointvector import Point3D


def test_orientation_simple():
    """Test the simple use of the orientation module."""
    # create a Room to assign different propeties by orientation.
    room = Room.from_box('ShoeBox', 5, 10, 3, 0, Point3D(0, 0, 3))

    # list of bcs properties to apply to faces of different orientations
    bcs = boundary_conditions
    boundaries = [bcs.outdoors, bcs.ground, bcs.outdoors, bcs.ground]
    ratios = [0.4, 0, 0.6, 0]

    # check that the inputs align with one another
    all_inputs = [boundaries, ratios]
    all_inputs, num_orient = check_matching_inputs(all_inputs)

    # assign proeprties based on orientation
    angles = angles_from_num_orient(num_orient)
    for face in room.faces:
        orient_i = face_orient_index(face, angles)
        if orient_i is not None:
            bc, ratio = inputs_by_index(orient_i, all_inputs)
            face.boundary_condition = bc
            if ratio != 0:
                face.apertures_by_ratio(ratio, 0.01)
    
    assert isinstance(room[1].boundary_condition, Outdoors)
    assert isinstance(room[2].boundary_condition, Ground)
    assert isinstance(room[3].boundary_condition, Outdoors)
    assert isinstance(room[4].boundary_condition, Ground)

    assert len(room[0].apertures) == 0
    assert len(room[1].apertures) == 1
    assert len(room[2].apertures) == 0
    assert len(room[3].apertures) == 1
    assert len(room[4].apertures) == 0
    assert len(room[5].apertures) == 0
