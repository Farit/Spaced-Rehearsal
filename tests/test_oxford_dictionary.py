"""
How to run tests:
    PYTHONPATH='.' python3.6 -m pytest -v tests/test_oxford_dictionary.py
"""
import os
import asyncio
import sqlite3

import pytest


from src.dictionary.base import ErrorCodes
from src.dictionary.oxford import OxfordEngDict


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def dictionary_db():
    dictionary_db_path = 'dictionary_test.db'
    yield dictionary_db_path
    os.remove(dictionary_db_path)


def test_oxford_eng_dict__close(event_loop, dictionary_db):
    dictionary = OxfordEngDict(
        api_base_url='https://od-api.oxforddictionaries.com/api/v2',
        app_id=os.getenv('OXFORD_DICTIONARY_APP_ID'),
        app_key=os.getenv('OXFORD_DICTIONARY_APP_KEY'),
        dictionary_db_path=dictionary_db
    )
    event_loop.run_until_complete(dictionary.close())
    with pytest.raises(sqlite3.ProgrammingError) as excinfo:
        event_loop.run_until_complete(dictionary.get_lemmas('looked'))

    assert str(excinfo.value).lower() == 'cannot operate on a closed cursor.'


def test_oxford_eng_dict__check_connection_success(event_loop, dictionary_db):
    dictionary = OxfordEngDict(
        api_base_url='https://od-api.oxforddictionaries.com/api/v2',
        app_id=os.getenv('OXFORD_DICTIONARY_APP_ID'),
        app_key=os.getenv('OXFORD_DICTIONARY_APP_KEY'),
        dictionary_db_path=dictionary_db
    )
    result = event_loop.run_until_complete(dictionary.check_connection())
    assert result['is_success']
    assert result['error'] is None


def test_oxford_eng_dict__check_connection_error(event_loop, dictionary_db):
    dictionary = OxfordEngDict(
        api_base_url='https://od-api.oxforddictionaries.com/api/v2',
        app_id=None,
        app_key=None,
        dictionary_db_path=dictionary_db
    )
    result = event_loop.run_until_complete(dictionary.check_connection())
    assert not result['is_success']
    assert result['error'] is not None


def test_oxford_eng_dict__get_lemmas_offline(event_loop, dictionary_db):
    dictionary = OxfordEngDict(
        api_base_url='https://od-api.oxforddictionaries.com/api/v2',
        app_id=os.getenv('OXFORD_DICTIONARY_APP_ID'),
        app_key=os.getenv('OXFORD_DICTIONARY_APP_KEY'),
        dictionary_db_path=dictionary_db
    )
    assert dictionary.offline_dict.hits == 0
    assert dictionary.num_api_requests == 0

    result = event_loop.run_until_complete(dictionary.get_lemmas('looked'))
    assert result['lemmas'] == ['look']
    assert result['error'] is None
    assert dictionary.offline_dict.hits == 0
    assert dictionary.num_api_requests == 1

    result = event_loop.run_until_complete(dictionary.get_lemmas('looked'))
    assert result['lemmas'] == ['look']
    assert result['error'] is None
    assert dictionary.offline_dict.hits == 1
    assert dictionary.num_api_requests == 1


def test_oxford_eng_dict__get_lemmas_without_pos(event_loop, dictionary_db):
    # Test get_lemma without specifying the part of speech.
    dictionary = OxfordEngDict(
        api_base_url='https://od-api.oxforddictionaries.com/api/v2',
        app_id=os.getenv('OXFORD_DICTIONARY_APP_ID'),
        app_key=os.getenv('OXFORD_DICTIONARY_APP_KEY'),
        dictionary_db_path=dictionary_db
    )
    result = event_loop.run_until_complete(dictionary.get_lemmas('books'))
    assert result['lemmas'] == ['book', 'book']
    assert result['error'] is None
    assert dictionary.offline_dict.hits == 0
    assert dictionary.num_api_requests == 1

    result = event_loop.run_until_complete(dictionary.get_lemmas('reading'))
    expected_lemmas = sorted(['reading', 'Reading', 'Reading', 'read'])
    assert sorted(result['lemmas']) == expected_lemmas
    assert result['error'] is None
    assert dictionary.offline_dict.hits == 0
    assert dictionary.num_api_requests == 2


def test_oxford_eng_dict__get_lemmas_with_pos(event_loop, dictionary_db):
    # Test get_lemma when the part of speech of a word known.
    dictionary = OxfordEngDict(
        api_base_url='https://od-api.oxforddictionaries.com/api/v2',
        app_id=os.getenv('OXFORD_DICTIONARY_APP_ID'),
        app_key=os.getenv('OXFORD_DICTIONARY_APP_KEY'),
        dictionary_db_path=dictionary_db
    )
    result = event_loop.run_until_complete(
        dictionary.get_lemmas('reading', oxford_pos='verb')
    )
    assert result['lemmas'] == ['read']
    assert result['error'] is None
    assert dictionary.offline_dict.hits == 0
    assert dictionary.num_api_requests == 1

    result = event_loop.run_until_complete(
        dictionary.get_lemmas('boys', oxford_pos='verb', force=True)
    )
    assert result['lemmas'] == ['boy']
    assert result['error'] is None
    assert dictionary.offline_dict.hits == 0
    assert dictionary.num_api_requests == 3

    result = event_loop.run_until_complete(dictionary.get_lemmas('boys'))
    assert result['lemmas'] == ['boy']
    assert result['error'] is None
    assert dictionary.offline_dict.hits == 1
    assert dictionary.num_api_requests == 3

    result = event_loop.run_until_complete(
        dictionary.get_lemmas('boys', oxford_pos='verb', force=False)
    )
    assert result['lemmas'] is None
    assert result['error'] is dictionary.error_codes.EMPTY_RESULT
    assert dictionary.offline_dict.hits == 1
    assert dictionary.num_api_requests == 4

    result = event_loop.run_until_complete(
        dictionary.get_lemmas('ghrei321d', oxford_pos='verb', force=False)
    )
    assert result['lemmas'] is None
    assert result['error'] is dictionary.error_codes.CANNOT_FIND_IN_DICT
    assert dictionary.offline_dict.hits == 1
    assert dictionary.num_api_requests == 5


def test_oxford_eng_dict__get_lemmas_unexisting_word(event_loop, dictionary_db):
    dictionary = OxfordEngDict(
        api_base_url='https://od-api.oxforddictionaries.com/api/v2',
        app_id=os.getenv('OXFORD_DICTIONARY_APP_ID'),
        app_key=os.getenv('OXFORD_DICTIONARY_APP_KEY'),
        dictionary_db_path=dictionary_db
    )
    result = event_loop.run_until_complete(dictionary.get_lemmas('aaabbbccc'))
    assert result['lemmas'] is None
    assert result['error'] is ErrorCodes.CANNOT_FIND_IN_DICT


def test_oxford_eng_dict__get_text_pronunciation(event_loop, dictionary_db):
    dictionary = OxfordEngDict(
        api_base_url='https://od-api.oxforddictionaries.com/api/v2',
        app_id=os.getenv('OXFORD_DICTIONARY_APP_ID'),
        app_key=os.getenv('OXFORD_DICTIONARY_APP_KEY'),
        dictionary_db_path=dictionary_db
    )
    result = event_loop.run_until_complete(
        dictionary.get_text_pronunciation('I like it.')
    )
    assert result == 'I: /ʌɪ/ like: /lʌɪk/ it: /ɪt/ .'


def test_oxford_eng_dict__get_word_pronunciation_without_gram_feature(
    event_loop, dictionary_db
):
    dictionary = OxfordEngDict(
        api_base_url='https://od-api.oxforddictionaries.com/api/v2',
        app_id=os.getenv('OXFORD_DICTIONARY_APP_ID'),
        app_key=os.getenv('OXFORD_DICTIONARY_APP_KEY'),
        dictionary_db_path=dictionary_db
    )
    eaten_pronunciation = 'ˈiːt'
    dictionary.offline_dict.set(
        key='eaten', value=eaten_pronunciation, field='pronunciation'
    )

    assert dictionary.offline_dict.hits == 0
    assert dictionary.num_api_requests == 0

    result = event_loop.run_until_complete(
        dictionary.get_word_pronunciation(
            word='eaten', oxford_pos='verb', treebank_pos='VBN'
        )
    )
    assert result['pronunciation'] == eaten_pronunciation
    assert result['error'] is None

    assert dictionary.offline_dict.hits == 1
    assert dictionary.num_api_requests == 0


def test_oxford_eng_dict__get_word_pronunciation(event_loop, dictionary_db):
    dictionary = OxfordEngDict(
        api_base_url='https://od-api.oxforddictionaries.com/api/v2',
        app_id=os.getenv('OXFORD_DICTIONARY_APP_ID'),
        app_key=os.getenv('OXFORD_DICTIONARY_APP_KEY'),
        dictionary_db_path=dictionary_db
    )
    assert dictionary.offline_dict.hits == 0
    assert dictionary.num_api_requests == 0

    result = event_loop.run_until_complete(
        dictionary.get_word_pronunciation('book')
    )
    assert result['pronunciation'] == 'bʊk'
    assert result['error'] is None

    assert dictionary.offline_dict.hits == 0
    assert dictionary.num_api_requests == 1

    result = event_loop.run_until_complete(
        dictionary.get_word_pronunciation('book')
    )
    assert result['pronunciation'] == 'bʊk'
    assert result['error'] is None

    assert dictionary.offline_dict.hits == 1
    assert dictionary.num_api_requests == 1

    result = event_loop.run_until_complete(
        dictionary.get_word_pronunciation(
            'liked', oxford_pos='verb', treebank_pos='VBD'
        )
    )
    assert result['pronunciation'] == 'lʌɪkt'
    assert result['error'] is None

    assert dictionary.offline_dict.hits == 1
    assert dictionary.num_api_requests == 5

    result = event_loop.run_until_complete(
        dictionary.get_word_pronunciation(
            'liked', oxford_pos='verb', treebank_pos='VBD'
        )
    )
    assert result['pronunciation'] == 'lʌɪkt'
    assert result['error'] is None

    assert dictionary.offline_dict.hits == 2
    assert dictionary.num_api_requests == 5


def test_oxford_eng_dict__construct_compound_word_pronunciation():
    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='looking',
        lemma='look',
        lemma_pronunciation='lʊk',
        word_treebank_pos='VBG'
    )
    assert word_pronunciation == 'lʊkɪŋ'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='coughed',
        lemma='cough',
        lemma_pronunciation='kɒf',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'kɒft'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='stopped',
        lemma='stop',
        lemma_pronunciation='stɒp',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'stɒpt'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='liked',
        lemma='like',
        lemma_pronunciation='lʌɪk',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'lʌɪkt'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='crossed',
        lemma='cross',
        lemma_pronunciation='krɒs',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'krɒst'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='released',
        lemma='release',
        lemma_pronunciation='rɪˈliːs',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'rɪˈliːst'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='reached',
        lemma='reach',
        lemma_pronunciation='riːtʃ',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'riːtʃt'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='washed',
        lemma='wash',
        lemma_pronunciation='wɒʃ',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'wɒʃt'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='bathed',
        lemma='bath',
        lemma_pronunciation='bɑːθ',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'bɑːθt'

    # Comparative and superlative adjectives
    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='bigger',
        lemma='big',
        lemma_pronunciation='bɪɡ',
        word_treebank_pos='JJR'
    )
    assert word_pronunciation == 'bɪɡə'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='happiest',
        lemma='happy',
        lemma_pronunciation='ˈhapi',
        word_treebank_pos='JJS'
    )
    assert word_pronunciation == 'ˈhapiəst'


    # Final 'ed' is pronounced /d/ after a voiced consonant or vowel.
    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='robbed',
        lemma='rob',
        lemma_pronunciation='rɒb',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'rɒbd'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='saved',
        lemma='save',
        lemma_pronunciation='seɪv',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'seɪvd'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='seized',
        lemma='seize',
        lemma_pronunciation='siːz',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'siːzd'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='called',
        lemma='call',
        lemma_pronunciation='kɔːl',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'kɔːld'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='planned',
        lemma='plan',
        lemma_pronunciation='plan',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'pland'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='occurred',
        lemma='occur',
        lemma_pronunciation='əˈkəː',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'əˈkəːd'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='managed',
        lemma='manage',
        lemma_pronunciation='ˈmanɪdʒ',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'ˈmanɪdʒd'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='played',
        lemma='play',
        lemma_pronunciation='pleɪ',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'pleɪd'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='tried',
        lemma='try',
        lemma_pronunciation='trʌɪ',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'trʌɪd'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='studied',
        lemma='study',
        lemma_pronunciation='ˈstʌdi',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'ˈstʌdid'

    # Final 'ed' is pronounced /id/ after the letters t and d.
    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='wanted',
        lemma='want',
        lemma_pronunciation='wɒnt',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'wɒntid'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='hated',
        lemma='hate',
        lemma_pronunciation='heɪt',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'heɪtid'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='counted',
        lemma='count',
        lemma_pronunciation='kaʊnt',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'kaʊntid'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='started',
        lemma='start',
        lemma_pronunciation='stɑːt',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'stɑːtid'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='needed',
        lemma='need',
        lemma_pronunciation='niːd',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'niːdid'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='loaded',
        lemma='load',
        lemma_pronunciation='ləʊd',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'ləʊdid'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='folded',
        lemma='fold',
        lemma_pronunciation='fəʊld',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'fəʊldid'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='added',
        lemma='add',
        lemma_pronunciation='ad',
        word_treebank_pos='VBD'
    )
    assert word_pronunciation == 'adid'

    # Final 's/es' is pronounced /s/ after a voiceless consonant
    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='tapes',
        lemma='tape',
        lemma_pronunciation='teɪp',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'teɪps'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='streets',
        lemma='street',
        lemma_pronunciation='striːt',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'striːts'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='parks',
        lemma='park',
        lemma_pronunciation='pɑːk',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'pɑːks'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='chiefs',
        lemma='chief',
        lemma_pronunciation='tʃiːf',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'tʃiːfs'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='myths',
        lemma='myth',
        lemma_pronunciation='mɪθ',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'mɪθs'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='leaves',
        lemma='leave',
        lemma_pronunciation='liːf',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'liːfs'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='grips',
        lemma='grip',
        lemma_pronunciation='ɡrɪp',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'ɡrɪps'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='writes',
        lemma='write',
        lemma_pronunciation='rʌɪt',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'rʌɪts'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='takes',
        lemma='take',
        lemma_pronunciation='teɪk',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'teɪks'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='sniffs',
        lemma='sniff',
        lemma_pronunciation='snɪf',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'snɪfs'

    # Final 's/es' is pronounced /z/ after a voiced consonant or vowel.
    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='ribs',
        lemma='rib',
        lemma_pronunciation='rɪb',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'rɪbz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='kids',
        lemma='kid',
        lemma_pronunciation='kɪd',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'kɪdz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='legs',
        lemma='leg',
        lemma_pronunciation='lɛɡ',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'lɛɡz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='clothes',
        lemma='cloth',
        lemma_pronunciation='kləʊ',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'kləʊz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='girls',
        lemma='girl',
        lemma_pronunciation='ɡəːl',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'ɡəːlz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='games',
        lemma='game',
        lemma_pronunciation='ɡeɪm',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'ɡeɪmz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='cars',
        lemma='car',
        lemma_pronunciation='kɑː',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'kɑːz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='boys',
        lemma='boy',
        lemma_pronunciation='bɔɪ',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'bɔɪz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='pies',
        lemma='pie',
        lemma_pronunciation='pʌɪ',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'pʌɪz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='cows',
        lemma='cow',
        lemma_pronunciation='kaʊ',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'kaʊz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='cities',
        lemma='city',
        lemma_pronunciation='ˈsɪti',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'ˈsɪtiz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='robs',
        lemma='rob',
        lemma_pronunciation='rɒb',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'rɒbz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='reads',
        lemma='read',
        lemma_pronunciation='riːd',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'riːdz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='digs',
        lemma='dig',
        lemma_pronunciation='dɪɡ',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'dɪɡz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='saves',
        lemma='save',
        lemma_pronunciation='seɪv',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'seɪvz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='falls',
        lemma='fall',
        lemma_pronunciation='fɔːl',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'fɔːlz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='plans',
        lemma='plan',
        lemma_pronunciation='plan',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'planz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='swims',
        lemma='swim',
        lemma_pronunciation='swɪm',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'swɪmz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='offers',
        lemma='offer',
        lemma_pronunciation='ˈɒfə',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'ˈɒfəz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='plays',
        lemma='play',
        lemma_pronunciation='pleɪ',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'pleɪz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='cries',
        lemma='cry',
        lemma_pronunciation='krʌɪ',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'krʌɪz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='goes',
        lemma='go',
        lemma_pronunciation='ɡəʊ',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'ɡəʊz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='copies',
        lemma='copy',
        lemma_pronunciation='ˈkɒpi',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'ˈkɒpiz'

    # Final 's/es' is pronounced /iz/ after the letters s, z, x, ch, tch,
    # ge, dge, sh

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='pieces',
        lemma='piece',
        lemma_pronunciation='piːs',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'piːsiz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='roses',
        lemma='rose',
        lemma_pronunciation='rəʊz',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'rəʊziz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='prizes',
        lemma='prize',
        lemma_pronunciation='prʌɪz',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'prʌɪziz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='boxes',
        lemma='box',
        lemma_pronunciation='bɒks',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'bɒksiz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='coaches',
        lemma='coach',
        lemma_pronunciation='kəʊtʃ',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'kəʊtʃiz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='bridges',
        lemma='bridg',
        lemma_pronunciation='brɪdʒ',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'brɪdʒiz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='dishes',
        lemma='dish',
        lemma_pronunciation='dɪʃ',
        word_treebank_pos='NNS'
    )
    assert word_pronunciation == 'dɪʃiz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='kisses',
        lemma='kiss',
        lemma_pronunciation='kɪs',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'kɪsiz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='loses',
        lemma='lose',
        lemma_pronunciation='luːz',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'luːziz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='relaxes',
        lemma='relax',
        lemma_pronunciation='rɪˈlaks',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'rɪˈlaksiz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='catches',
        lemma='catch',
        lemma_pronunciation='katʃ',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'katʃiz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='judges',
        lemma='judge',
        lemma_pronunciation='dʒʌdʒ',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'dʒʌdʒiz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='manages',
        lemma='manage',
        lemma_pronunciation='ˈmanɪdʒ',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'ˈmanɪdʒiz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='flashes',
        lemma='flash',
        lemma_pronunciation='flaʃ',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'flaʃiz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='washes',
        lemma='wash',
        lemma_pronunciation='wɒʃ',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'wɒʃiz'

    word_pronunciation = OxfordEngDict._construct_compound_word_pronunciation(
        word='rouges',
        lemma='rouge',
        lemma_pronunciation='ruːʒ',
        word_treebank_pos='VBZ'
    )
    assert word_pronunciation == 'ruːʒiz'

