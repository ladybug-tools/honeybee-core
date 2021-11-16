# coding: utf-8
"""Base class for all geometry objects that can have shades as children."""
from ._base import _Base
from .shade import Shade
from .typing import invalid_dict_error


class _BaseWithShade(_Base):
    """A base class for all objects that can have Shades nested on them.

    Args:
        identifier: Text string for a unique object ID. Must be < 100 characters and
            not contain any spaces or special characters.

    Properties:
        * identifier
        * display_name
        * geometry
        * outdoor_shades
        * indoor_shades
        * shades
    """
    __slots__ = ('_outdoor_shades', '_indoor_shades')

    def __init__(self, identifier):
        """Initialize base with shade object."""
        _Base.__init__(self, identifier)  # process the identifier
        self._outdoor_shades = []
        self._indoor_shades = []

    @property
    def outdoor_shades(self):
        """Get an array of all outdoor shades assigned to this object."""
        return tuple(self._outdoor_shades)

    @property
    def indoor_shades(self):
        """Get an array of all indoor shades assigned to this object."""
        return tuple(self._indoor_shades)

    @property
    def shades(self):
        """Get an array of all shades (indoor + outdoor) assigned to this object."""
        return self._outdoor_shades + self._indoor_shades

    def remove_shades(self):
        """Remove all indoor and outdoor shades assigned to this object."""
        self.remove_indoor_shades()
        self.remove_outdoor_shades()

    def remove_outdoor_shades(self):
        """Remove all outdoor shades assigned to this object."""
        for shade in self._outdoor_shades:
            shade._parent = None
        self._outdoor_shades = []

    def remove_indoor_shades(self):
        """Remove all indoor shades assigned to this object."""
        for shade in self._indoor_shades:
            shade._parent = None
            shade._is_indoor = False
        self._indoor_shades = []

    def add_outdoor_shade(self, shade):
        """Add a Shade object to the outdoors of this object.

        Outdoor Shade objects can be used to represent balconies, outdoor furniture,
        overhangs, light shelves, fins, the exterior part of mullions, etc.
        For representing larger shade objects like trees or other buildings,
        it may be more appropriate to add them to the Model as orphaned_shades
        without a specific parent object.

        Args:
            shade: A Shade object to add to the outdoors of this object.
        """
        assert isinstance(shade, Shade), \
            'Expected Shade for outdoor_shade. Got {}.'.format(type(shade))
        assert shade.parent is None, 'Shade cannot have more than one parent object.'
        shade._parent = self
        shade._is_detached = False
        self._outdoor_shades.append(shade)

    def add_indoor_shade(self, shade):
        """Add a Shade object to be added to the indoors of this object.

        Indoor Shade objects can be used to represent furniture, the interior
        portion of light shelves, the interior part of mullions, etc.
        For representing finely detailed objects like blinds or roller shades,
        it may be more appropriate to model them as materials assigned to
        Aperture properties (like Radiance materials or Energy constructions).

        Args:
            shade: A Shade object to add to the indoors of this object.
        """
        assert isinstance(shade, Shade), \
            'Expected Shade for indoor_shade. Got {}.'.format(type(shade))
        assert shade.parent is None, 'Shade cannot have more than one parent object.'
        shade._parent = self
        shade._is_detached = False
        shade._is_indoor = True
        self._indoor_shades.append(shade)

    def add_outdoor_shades(self, shades):
        """Add a list of Shade objects to the outdoors of this object.

        Args:
            shades: A list of Shade objects to add to the outdoors of this object.
        """
        for shade in shades:
            self.add_outdoor_shade(shade)

    def add_indoor_shades(self, shades):
        """Add a list of Shade objects to the indoors of this object.

        Args:
            shades: A list of Shade objects to add to the indoors of this object.
        """
        for shade in shades:
            self.add_indoor_shade(shade)

    def move_shades(self, moving_vec):
        """Move all indoor and outdoor shades assigned to this object along a vector.

        Args:
            moving_vec: A ladybug_geometry Vector3D with the direction and distance
                to move the shades.
        """
        for oshd in self._outdoor_shades:
            oshd.move(moving_vec)
        for ishd in self._indoor_shades:
            ishd.move(moving_vec)

    def rotate_shades(self, axis, angle, origin):
        """Rotate all indoor and outdoor shades assigned to this object.

        Args:
            axis: A ladybug_geometry Vector3D axis representing the axis of rotation.
            angle: An angle for rotation in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        for oshd in self._outdoor_shades:
            oshd.rotate(axis, angle, origin)
        for ishd in self._indoor_shades:
            ishd.rotate(axis, angle, origin)

    def rotate_xy_shades(self, angle, origin):
        """Rotate all indoor and outdoor shades counterclockwise in the world XY plane.

        Args:
            angle: An angle in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        for oshd in self._outdoor_shades:
            oshd.rotate_xy(angle, origin)
        for ishd in self._indoor_shades:
            ishd.rotate_xy(angle, origin)

    def reflect_shades(self, plane):
        """Reflect all indoor and outdoor shades assigned to this object across a plane.

        Args:
            plane: A ladybug_geometry Plane across which the object will
                be reflected.
        """
        for oshd in self._outdoor_shades:
            oshd.reflect(plane)
        for ishd in self._indoor_shades:
            ishd.reflect(plane)

    def scale_shades(self, factor, origin=None):
        """Scale all indoor and outdoor shades assigned to this object by a factor.

        Args:
            factor: A number representing how much the object should be scaled.
            origin: A ladybug_geometry Point3D representing the origin from which
                to scale. If None, it will be scaled from the World origin (0, 0, 0).
        """
        for oshd in self._outdoor_shades:
            oshd.scale(factor, origin)
        for ishd in self._indoor_shades:
            ishd.scale(factor, origin)

    def _add_prefix_shades(self, prefix):
        """Change the name of all child shades by inserting a prefix.

        Args:
            prefix: Text that will be inserted at the start of this shades' name
                and display_name.
        """
        for shade in self._outdoor_shades:
            shade.add_prefix(prefix)
        for shade in self._indoor_shades:
            shade.add_prefix(prefix)

    def _check_planar_shades(self, tolerance):
        """Check that all of the child shades are planar."""
        msgs = []
        for oshd in self._outdoor_shades:
            msgs.append(oshd.check_planar(tolerance, False))
        for ishd in self._indoor_shades:
            msgs.append(ishd.check_planar(tolerance, False))
        return '\n'.join([m for m in msgs if m != ''])

    def _check_self_intersecting_shades(self, tolerance):
        """Check that no edges of the indoor or outdoor shades self-intersect."""
        msgs = []
        for oshd in self._outdoor_shades:
            msgs.append(oshd.check_self_intersecting(tolerance, False))
        for ishd in self._indoor_shades:
            msgs.append(ishd.check_self_intersecting(tolerance, False))
        return '\n'.join([m for m in msgs if m != ''])

    def _check_non_zero_shades(self, tolerance=0.0001):
        """Check that the indoor or outdoor shades are above a "zero" area tolerance."""
        msgs = []
        for oshd in self._outdoor_shades:
            msgs.append(oshd.check_non_zero(tolerance, False))
        for ishd in self._indoor_shades:
            msgs.append(ishd.check_non_zero(tolerance, False))
        return '\n'.join([m for m in msgs if m != ''])

    def _add_shades_to_dict(
            self, base, abridged=False, included_prop=None, include_plane=True):
        """Method used to add child shades to the parent base dictionary.

        Args:
            base: The base object dictionary to which the child shades will be added.
            abridged: Boolean to note whether the extension properties of the
                object should be included in detail (False) or just referenced by
                identifier (True). (Default: False).
            included_prop: List of properties to filter keys that must be included in
                output dictionary. For example ['energy'] will include 'energy' key if
                available in properties to_dict. By default all the keys will be
                included. To exclude all the keys from extensions use an empty list.
            include_plane: Boolean to note wether the plane of the Face3D should be
                included in the output. This can preserve the orientation of the
                X/Y axes of the plane but is not required and can be removed to
                keep the dictionary smaller. (Default: True).
        """
        if self._outdoor_shades != []:
            base['outdoor_shades'] = [shd.to_dict(abridged, included_prop, include_plane)
                                      for shd in self._outdoor_shades]
        if self._indoor_shades != []:
            base['indoor_shades'] = [shd.to_dict(abridged, included_prop, include_plane)
                                     for shd in self._indoor_shades]

    def _recover_shades_from_dict(self, data):
        """Method used to recover shades from a dictionary.

        Args:
            data: The dictionary representation of this object to which shades will
                be added from the dictionary.
        """
        if 'outdoor_shades' in data and data['outdoor_shades'] is not None:
            for sh in data['outdoor_shades']:
                try:
                    oshd = Shade.from_dict(sh)
                    oshd._parent = self
                    self._outdoor_shades.append(oshd)
                except Exception as e:
                    invalid_dict_error(sh, e)
        if 'indoor_shades' in data and data['indoor_shades'] is not None:
            for sh in data['indoor_shades']:
                try:
                    ishd = Shade.from_dict(sh)
                    ishd._parent = self
                    ishd._is_indoor = True
                    self._indoor_shades.append(ishd)
                except Exception as e:
                    invalid_dict_error(sh, e)

    def _duplicate_child_shades(self, new_object):
        """Add duplicated child shades to a duplicated new_object."""
        new_object._outdoor_shades = [oshd.duplicate() for oshd in self._outdoor_shades]
        new_object._indoor_shades = [ishd.duplicate() for ishd in self._indoor_shades]
        for oshd in new_object._outdoor_shades:
            oshd._parent = new_object
        for ishd in new_object._indoor_shades:
            ishd._parent = new_object
            ishd._is_indoor = True
