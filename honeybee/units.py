"""Utility functions for converting and parsing units of length."""

# global properties to set all supported units
UNITS = ('Meters', 'Millimeters', 'Feet', 'Inches', 'Centimeters')
UNITS_ABBREVIATIONS = ('m', 'mm', 'ft', 'in', 'cm')
UNITS_TOLERANCES = {
    'Meters': 0.01,
    'Millimeters': 1.0,
    'Feet': 0.01,
    'Inches': 0.1,
    'Centimeters': 1.0
}


def conversion_factor_to_meters(units):
    """Get the conversion factor to meters based on input units.

    Args:
        units: Text for the units. Choose from the following:

            * Meters
            * Millimeters
            * Feet
            * Inches
            * Centimeters

    Returns:
        A number for the conversion factor, which should be multiplied by
        all distance units taken from Rhino geometry in order to convert
        them to meters.
    """
    if units == 'Meters':
        return 1.0
    elif units == 'Millimeters':
        return 0.001
    elif units == 'Feet':
        return 0.305
    elif units == 'Inches':
        return 0.0254
    elif units == 'Centimeters':
        return 0.01
    else:
        raise ValueError(
            'You are kidding me! What units are you using? {}?\n'
            'Please use one of the following: {}'.format(units, ' '.join(UNITS))
        )


def parse_distance_string(distance_string, destination_units='Meters'):
    """Parse a string of a distance value into a destination units system.

    Args:
        distance_string: Text for a distance value to be parsed into the
            destination units. This can have the units at the end of
            it (eg. "3ft"). If no units are included, the number will be
            assumed to be in the destination units system.
        destination_units: The destination units system to which the distance
            string will be computed. (Default: Meters).

    Returns:
        A number for the distance in the destination_units.
    """
    # separate the distance string into a number and a unit abbreviation
    distance_string = distance_string.strip()
    try:  # check if the distance string is just a number
        return float(distance_string)
    except ValueError:  # it must have some units attached to it
        for i, ua in enumerate(UNITS_ABBREVIATIONS):
            try:  # see if replacing the units yields a float
                distance = float(distance_string.replace(ua, '', 1))
                u_sys = UNITS[i]
                break
            except ValueError:  # not the right type of units
                pass
        else:  # we could not match the units system
            raise ValueError(
                'Text string "{}" could not be decoded into a distance and a unit.\n'
                'Make sure your units are one of the following: {}'.format(
                    distance_string, ' '.join(UNITS_ABBREVIATIONS))
            )

    # process the number into the destination units system
    if u_sys == destination_units:
        return distance
    con_factor = 1 / conversion_factor_to_meters(destination_units)
    if u_sys != 'Meters':
        con_factor = con_factor * conversion_factor_to_meters(u_sys)
    return distance * con_factor
