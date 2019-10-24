"""Test the search functions."""
from honeybee.search import filter_array_by_keywords, any_keywords_in_string


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
    assert any_keywords_in_string(elements, keywords_3)
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
    assert filter_array_by_keywords(elements, keywords_2) == ['Fire', 'Water']
    assert filter_array_by_keywords(elements, keywords_3) == ['Water']
    assert filter_array_by_keywords(elements, keywords_4) == ['Fire']
    assert filter_array_by_keywords(elements, keywords_4, False) == []
    assert filter_array_by_keywords(elements, keywords_5) == []
    assert filter_array_by_keywords(elements, keywords_6) == []
