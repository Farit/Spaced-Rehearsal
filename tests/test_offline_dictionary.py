"""
How to run tests:
    PYTHONPATH='.' python3.6 -m pytest -v tests/test_offline_dictionary.py
"""
import os

import pytest

from src.dictionary.offline_dictionary import OfflineDict


@pytest.fixture
def dictionary_db():
    dictionary_db_path = 'dictionary_test.db'
    yield dictionary_db_path
    os.remove(dictionary_db_path)


def test_offline_dictionary(dictionary_db):
    offline_dict = OfflineDict(lang='en', dictionary_db_path=dictionary_db)

    res = offline_dict.get(key='book')
    assert res is offline_dict.missing_value_sentinel

    offline_dict.set(key='book', value=["buk"])
    res = offline_dict.get(key='book')
    assert res == ['buk']

    offline_dict.set(key='book', value={"value": "buk"})
    res = offline_dict.get(key='book')
    assert res == {"value": "buk"}

    res = offline_dict.get(key='book', field='pronunciation')
    assert res is offline_dict.missing_value_sentinel

    offline_dict.set(key='book', value=["book pronun"], field='pronunciation')
    res = offline_dict.get(key='book', field='pronunciation')
    assert res == ['book pronun']

    offline_dict.set(
        key='book', value={"value": "book pronun"}, field='pronunciation'
    )
    res = offline_dict.get(key='book', field='pronunciation')
    assert res == {"value": "book pronun"}

    res = offline_dict.get(key='book', grammatical_feature='noun')
    assert res is offline_dict.missing_value_sentinel

    offline_dict.set(
        key='book', value=["book noun"], grammatical_feature='noun'
    )
    res = offline_dict.get(key='book', grammatical_feature='noun')
    assert res == ["book noun"]

    offline_dict.set(
        key='book', value={"value": "book noun"}, grammatical_feature='noun'
    )
    res = offline_dict.get(key='book', grammatical_feature='noun')
    assert res == {"value": "book noun"}

    res = offline_dict.get(
        key='book', field='pronunciation', grammatical_feature='noun'
    )
    assert res is offline_dict.missing_value_sentinel

    offline_dict.set(
        key='book', value="book pronun noun",
        field='pronunciation',
        grammatical_feature='noun'
    )
    res = offline_dict.get(
        key='book', field='pronunciation', grammatical_feature='noun'
    )
    assert res == "book pronun noun"

    offline_dict.set(
        key='book', value={"value": "book pronun noun"},
        field='pronunciation',
        grammatical_feature='noun'
    )

    res = offline_dict.get(key='book')
    assert res == {"value": "buk"}
    res = offline_dict.get(key='book', field='pronunciation')
    assert res == {"value": "book pronun"}
    res = offline_dict.get(key='book', grammatical_feature='noun')
    assert res == {"value": "book noun"}
    res = offline_dict.get(
        key='book', field='pronunciation', grammatical_feature='noun'
    )
    assert res == {"value": "book pronun noun"}
