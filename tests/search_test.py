"""Test the search functions."""
from honeybee.search import filter_array_by_keywords, any_keywords_in_string, \
    get_attr_nested

from collections import namedtuple


def test_any_keywords_in_string():
    """Test the any_keywords_in_string method."""
    elements = 'Fire Water Air Earth'
    keywords_1 = ('Fire',)
    keywords_2 = ('Fire', 'Water')
    keywords_3 = ('Hydrogen', 'Water')
    keywords_4 = ('FireHydrogen',)
    keywords_5 = ('Hydrogen',)

    assert any_keywords_in_string(elements, keywords_1)
    assert any_keywords_in_string(elements, keywords_2)
    assert not any_keywords_in_string(elements, keywords_3)
    assert not any_keywords_in_string(elements, keywords_4)
    assert not any_keywords_in_string(elements, keywords_5)


def test_filter_array_by_keywords():
    """Test the filter_array_by_keywords method."""
    elements = ('Fire', 'Water', 'Air', 'Earth', 'Heart')
    keywords_1 = ('Fire',)
    keywords_2 = ('Fire', 'Water')
    keywords_3 = ('Hydrogen', 'Water')
    keywords_4 = ('Fire Hydrogen',)
    keywords_5 = ('FireHydrogen',)
    keywords_6 = ('Hydrogen', 'Helium')

    assert filter_array_by_keywords(elements, keywords_1) == ['Fire']
    assert filter_array_by_keywords(elements, keywords_2) == []
    assert filter_array_by_keywords(elements, keywords_3) == []
    assert filter_array_by_keywords(elements, keywords_4) == []
    assert filter_array_by_keywords(elements, keywords_4, False) == []
    assert filter_array_by_keywords(elements, keywords_5) == []
    assert filter_array_by_keywords(elements, keywords_6) == []


def test_get_attr_nested():
    """Test the get_attr_nested method."""
    TestObject = namedtuple('SampleObject', ['user_data'])
    to_ = TestObject(
        user_data={
            'tag': 'A1', '__layer__': 'Default',
            'data': {'name': 'none-of-your-business'}
        }
    )

    assert get_attr_nested(to_, 'user_data.tag') == 'A1'
    assert get_attr_nested(to_, 'user_data.__layer__') == 'Default'
    assert get_attr_nested(to_, 'user_data.data.name') == 'none-of-your-business'
    assert get_attr_nested(to_, 'user_data.layer') == 'None'
