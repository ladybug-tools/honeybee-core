"""Collection of methods for searching for keywords and filtering lists by keywords.
This module also included methods to get nested attributes of objects.

This is useful for cases like the following:

* Searching through the honeybee-radiance modifier library.
* Searching through the honeybee-energy material, construction, schedule,
  constructionset, or programtype libraries.
* Searching through EnergyPlus IDD or RDD to find possible output variables
  to request form the simulation.
"""


def filter_array_by_keywords(array, keywords, parse_phrases=True):
    """Filter an array of strings to get only those containing the given keywords.

    This method is case insensitive, allowing the searching of keywords across
    different cases of letters.

    Args:
        array: An array of strings which will be filtered to get only those containing
            the given keywords.
        keywords: An array of strings representing keywords.
        parse_phrases: If True, this method will automatically parse any strings of
            multiple keywords (separated by spaces) into separate keywords for
            searching. This results in a greater likelihood that someone finds what
            they are searching for in large arrays but it may not be appropriate for
            all cases. You may want to set it to False when you are searching for a
            specific phrase that includes spaces. Default: True.
    """
    # split any keywords separated by spaces
    if parse_phrases:
        keywords = [kw for words in keywords for kw in words.upper().split()]
    else:
        keywords = [kw.upper() for kw in keywords]

    # filter the input array
    return [item for item in array if any_keywords_in_string(item.upper(), keywords)]


def any_keywords_in_string(name, keywords):
    """Check whether any keywords in an array exist within a given string.

    Args:
        name: A string which will be tested for whether it possesses any of the keywords.
        keywords: An array of strings representing keywords, which will be searched for
            in the name.
    """
    return all(kw in name for kw in keywords)


def get_attr_nested(obj_instance, attr_name, decimal_count=None, cast_to_str=True):
    """Get the attribute of an object while allowing the request of nested attributes.

    Args:
        obj_instance: An instance of a Python object. Typically, this is a honeybee
            object like a Model, Room, Face, Aperture, Door, or Shade.
        attr_name: A string of an attribute that the input obj_instance should have.
            This can have '.' that separate the nested attributes from one another.
            For example, 'properties.energy.construction'.
        decimal_count: An optional integer to be used to round the property to a
            number of decimal places if it is a float. (Default: None).
        cast_to_str: Boolean to note whether attributes with a type other than
            float should be cast to strings. If False, the attribute will be
            returned with the original object type. (Default: True).

    Returns:
        A string or number for tha attribute assigned ot the obj_instance. If the
        input attr_name is a valid attribute for the object but None is assigned,
        the output will be 'None'. If the input attr_name is not valid for
        the input object, 'N/A' will be returned.
    """
    if '.' in attr_name:  # nested attribute
        attributes = attr_name.split('.')  # get all the sub-attributes
        current_obj = obj_instance
        try:
            for attribute in attributes:
                if current_obj is None:
                    raise AttributeError
                elif isinstance(current_obj, dict):
                    current_obj = current_obj.get(attribute, None)
                else:
                    current_obj = getattr(current_obj, attribute)
            if isinstance(current_obj, float) and decimal_count:
                return round(current_obj, decimal_count)
            else:
                return str(current_obj) if cast_to_str else current_obj
        except AttributeError as e:
            if 'NoneType' in str(e):  # it's a valid attribute but it's not assigned
                return 'None'
            else:  # it's not a valid attribute
                return 'N/A'
    else:  # honeybee-core attribute
        try:
            current_obj = getattr(obj_instance, attr_name)
            if isinstance(current_obj, float) and decimal_count:
                return round(current_obj, decimal_count)
            else:
                return str(current_obj) if cast_to_str else current_obj
        except AttributeError:
            return 'N/A'
