"""Collection of methods for searching for keywords and filtering lists by keywords.

This is useful for cases like the following:

* Searching through the honeybee-radiance modifier library.
* Searching through the honeybee-energy material, construction, schedule,
  constructionset, or programtype libraries.
* Searching through EnergyPlus IDD or RDD to find possilbe output variables
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
            multiple keywords (spearated by spaces) into separate keywords for
            searching. This results in a greater liklihood that someone finds what
            they are searching for in large arrays but it may not be appropropriate for
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
        name: A string which will be tested for whether it posseses any of the keywords.
        keywords: An array of strings representing keywords, which will be searched for
            in the name.
    """
    for kw in keywords:
        if kw in name:
            return True
    return False
