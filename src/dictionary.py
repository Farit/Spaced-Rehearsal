import enum
import logging
import json
import string
import socket
import os
import doctest
import sqlite3
import urllib.parse

from abc import ABC, abstractmethod

import nltk

from nltk.corpus import wordnet
from nltk.tokenize import word_tokenize
from tornado.httpclient import (
    AsyncHTTPClient, HTTPRequest, HTTPResponse, HTTPError
)

logger = logging.getLogger(__name__)


class ErrorCodes(enum.Enum):
    EMPTY_RESULT = 'empty_result'
    CANNOT_FIND_IN_DICT = 'cannot_find_in_dict'
    LEMMA_MISSING_PRONUNCIATION = 'lemma_missing_pronunciation'


class DictionaryAbstract(ABC):
    error_codes = ErrorCodes

    def __init__(self, lang, dictionary_db_path):
        self.cache = Cache(lang=lang, dictionary_db_path=dictionary_db_path)
        self.async_http_client = AsyncHTTPClient()
        self.num_api_requests = 0

    @abstractmethod
    async def check_connection(self) -> dict:
        """
        Varifies connection to the dictionary api with provided credentials. 
        Returns on successful connection:
            {'is_success': True, 'error': None}
        Otherwise:
            {'is_success': False, 'error': <error>}
        """
        pass

    @abstractmethod
    async def get_lemmas(self, word: str, oxford_pos: str=None) -> dict:
        """
        Returns the possible lemmas ("root" forms) for a given inflected word.
        (e.g., swimming -> swim).
        Lemma is a general term for any headword, phrase, or other form
        that can be looked up in a dictionary.
        An inflection is a change in the form of a word to express a 
        grammatical function such as tense, mood, purson, number, case or 
        gender. (e.g., 'boxes' is an inflected form of 'box')

        Parameter 'oxford_pos' can be used to specify the part of speech of 
        a word classified by Oxford Dictionary.

        Returns on success:
            {'lemmas': <lemmas>, 'error': None}
        Otherwise:
            {'lemmas': None, 'error': <error>}
        """
        pass

    @abstractmethod
    async def get_pronunciation(
        self, word: str, oxford_pos: str=None, treebank_pos: str=None
    ) -> dict:
        """
        Returns pronunciation of a word (e.g., book -> bʊk).
        Parameter 'oxford_pos' can be used to specify the part of speech of 
        a word classified by Oxford Dictionary.
        Parameter 'treebank_pos' can be used to specify the part of speech of 
        a word classified by Treebank.

        Returns on success:
            {'pronunciation': <pronunciation>, 'error': None}
        Otherwise:
            {'pronunciation': None, 'error': <error>}
        """
        pass

    @abstractmethod
    async def get_text_pronunciation(self, text: str) -> str:
        """
        Returns pronunciation of a text.
        """
        pass


    async def close(self):
        """
        Cleanup method.
        """
        await self.cache.close()


class OxfordEngDict(DictionaryAbstract):
    """
    Docs: https://developer.oxforddictionaries.com/documentation
    """
    source_lang = 'en'

    def __init__(self, api_base_url, app_id, app_key, dictionary_db_path):
        super().__init__(
            lang=self.source_lang,
            dictionary_db_path=dictionary_db_path
        )
        self.api_base_url = api_base_url
        self.app_id = app_id
        self.app_key = app_key

    async def check_connection(self) -> dict:
        """
        >>> import asyncio
        >>> loop = asyncio.new_event_loop()
        >>> app_id = os.getenv('OXFORD_DICTIONARY_APP_ID')
        >>> app_key = os.getenv('OXFORD_DICTIONARY_APP_KEY')
        >>> api_base_url = 'https://od-api.oxforddictionaries.com/api/v2'
        >>> dictionary = OxfordEngDict(
        ... api_base_url, app_id, app_key, dictionary_db_path='dictionary_test.db')
        >>> loop.run_until_complete(dictionary.check_connection())
        {'is_success': True, 'error': None}
        >>> app_id = None
        >>> app_key = None
        >>> api_base_url = 'https://od-api.oxforddictionaries.com/api/v2'
        >>> dictionary = OxfordEngDict(
        ... api_base_url, app_id, app_key, dictionary_db_path='dictionary_test.db')
        >>> res = loop.run_until_complete(dictionary.check_connection())
        >>> print(res['is_success'])
        False
        >>> loop.run_until_complete(dictionary.close())
        >>> loop.close()
        >>> import os
        >>> os.remove('dictionary_test.db')
        """
        res = {'is_success': True, 'error': None}

        url = f'{self.api_base_url}/lemmas/{self.source_lang}/book'
        http_request = self.form_http_request(url)
        response = await self.fetch_response(http_request)

        if not response['is_success']:
            res['is_success'] = False
            res['error'] = response['error']

        return res

    async def get_lemmas(self, word: str, oxford_pos: str=None) -> dict:
        """
        oxford_pos: the part of speech (‘noun’, ‘verb’, ‘adjective’ etc.) 
                    of a word classified by Oxford Dictionary.

        >>> import asyncio
        >>> loop = asyncio.new_event_loop()
        >>> app_id = os.getenv('OXFORD_DICTIONARY_APP_ID')
        >>> app_key = os.getenv('OXFORD_DICTIONARY_APP_KEY')
        >>> api_base_url = 'https://od-api.oxforddictionaries.com/api/v2'
        >>> dictionary = OxfordEngDict(
        ... api_base_url, app_id, app_key, dictionary_db_path='dictionary_test.db')

        # Test cache
        >>> print(dictionary.cache)
        CacheInfo(hits=0, misses=0, currsets=0)
        >>> loop.run_until_complete(dictionary.get_lemmas('looked'))
        {'lemmas': ['look'], 'error': None}
        >>> print(dictionary.cache)
        CacheInfo(hits=0, misses=1, currsets=1)
        >>> loop.run_until_complete(dictionary.get_lemmas('looked'))
        {'lemmas': ['look'], 'error': None}
        >>> print(dictionary.cache)
        CacheInfo(hits=1, misses=1, currsets=1)

        # Get lemma without specifying the part of speech.
        >>> loop.run_until_complete(dictionary.get_lemmas('books'))
        {'lemmas': ['book', 'book'], 'error': None}
        >>> loop.run_until_complete(dictionary.get_lemmas('reading'))
        {'lemmas': ['reading', 'Reading', 'Reading', 'read'], 'error': None}

        # Get lemma when the part of speech of a word known.
        >>> loop.run_until_complete(dictionary.get_lemmas('reading', oxford_pos='verb'))
        {'lemmas': ['read'], 'error': None}

        # Get lemma of an unexisting word.
        >>> loop.run_until_complete(dictionary.get_lemmas('aaabbbccc'))
        {'lemmas': None, 'error': <ErrorCodes.CANNOT_FIND_IN_DICT: 'cannot_find_in_dict'>}

        # Do clean up after running tests.
        >>> loop.run_until_complete(dictionary.close())
        >>> loop.close()
        >>> import os
        >>> os.remove('dictionary_test.db')
        """
        cache_key = f'lemmas__{word}'
        if oxford_pos:
            cache_key += f'__{oxford_pos}'

        result = {
            'lemmas': self.cache.get(key=cache_key),
            'error': None
        }

        if result['lemmas'] is self.cache.missing_value_sentinel:
            url = f'{self.api_base_url}/lemmas/{self.source_lang}/{word}'
            if oxford_pos:
                query_params = {'lexicalCategory': oxford_pos}
                query = urllib.parse.urlencode(query_params)
                http_request = self.form_http_request(f'{url}?{query}')
            else:
                http_request = self.form_http_request(url)

            response = await self.fetch_response(http_request)

            if response['is_success']:
                response = response['response']

                if len(response['results']) > 0:
                    lemmas = []
                    for lexical_entry in response['results'][0]['lexicalEntries']:
                        inflection = lexical_entry['inflectionOf']
                        root_form = inflection[0]['id']
                        lemmas.append(root_form)

                    self.cache.set(key=cache_key, value=lemmas)
                    result['lemmas'] = lemmas

                else:
                    result['lemmas'] = None
                    result['error'] = ErrorCodes.EMPTY_RESULT
            else:
                result['lemmas'] = None
                result['error'] = response['error']

        if not result['lemmas']:
            logger.error(
                f'Http request url: {http_request.url}, '
                f'result: {result} '
                f'context: word={word}, oxford_pos={oxford_pos}'
            )

        return result

    async def get_text_pronunciation(self, text: str) -> str:
        """
        >>> import asyncio
        >>> loop = asyncio.new_event_loop()
        >>> app_id = os.getenv('OXFORD_DICTIONARY_APP_ID')
        >>> app_key = os.getenv('OXFORD_DICTIONARY_APP_KEY')
        >>> api_base_url = 'https://od-api.oxforddictionaries.com/api/v2'
        >>> dictionary = OxfordEngDict(
        ... api_base_url, app_id, app_key, dictionary_db_path='dictionary_test.db')

        # Test cases.
        >>> loop.run_until_complete(dictionary.get_text_pronunciation(
        ... 'I like it.'
        ... ))
        'I: /ʌɪ/ like: /lʌɪk/ it: /ɪt/ .'
        >>> loop.run_until_complete(dictionary.get_text_pronunciation(
        ... 'I am reading a book.'
        ... ))
        'I: /ʌɪ/ am: /am/ reading: /riːdɪŋ/ a: /ə/ book: /bʊk/ .'
        >>> loop.run_until_complete(dictionary.get_text_pronunciation(
        ... 'An everyday object such as a spoon.'
        ... ))
        'An: /an/ everyday: /ˈɛvrɪdeɪ/ object: /ˈɒbdʒɛkt/ such: /sʌtʃ/ as: /az/ a: /ə/ spoon: /spuːn/ .'
        >>> loop.run_until_complete(dictionary.get_text_pronunciation(
        ... 'I will pay for the tickets.'
        ... ))
        'I: /ʌɪ/ will: /wɪl/ pay: /peɪ/ for: /fɔː/ the: /ðə/ tickets: /ˈtɪkɪts/ .'
        >>> loop.run_until_complete(dictionary.get_text_pronunciation(
        ... 'I lived there till May.'
        ... ))
        'I: /ʌɪ/ lived: /lɪvd/ there: /ðɛː/ till: /tɪl/ May: /meɪ/ .'
        >>> loop.run_until_complete(dictionary.get_text_pronunciation(
        ... 'Friends are important.'
        ... ))
        'Friends: /frɛndz/ are: /ɑː/ important: /ɪmˈpɔːt(ə)nt/ .'
        >>> loop.run_until_complete(dictionary.get_text_pronunciation(
        ... 'I like my classes.'
        ... ))
        'I: /ʌɪ/ like: /lʌɪk/ my: /mʌɪ/ classes: /klɑːsiz/ .'

        # Do clean up after running tests.
        >>> loop.run_until_complete(dictionary.close())
        >>> loop.close()
        >>> import os
        >>> os.remove('dictionary_test.db')
        """
        output = []

        # Break text into tokens.
        tokenized_text = word_tokenize(text)

        # Part-of-Speech(POS) tagging.
        # Identify the grammatical group of a given word.
        tokenized_text_pos = nltk.pos_tag(tokenized_text)

        for token, treebank_pos in tokenized_text_pos:
            # Filter token that is not a word.
            if treebank_pos in string.punctuation:
                output.append((token, None))
                continue

            try:
                oxford_pos = self._map_treebank_pos_into_oxford_pos(
                    treebank_pos
                )
            except Exception as err:
                logger.error(err)
                output.append((token, None))
                continue

            res = await self.get_pronunciation(
                word=token, oxford_pos=oxford_pos, treebank_pos=treebank_pos
            )

            if res['pronunciation'] is not None:
                output.append((token, f"/{res['pronunciation']}/"))
            else:
                logger.error(
                    f'Pronunciation: '
                    f'result: {res} '
                    f'context: word={token}, oxford_pos={oxford_pos} '
                    f'treebank_pos={treebank_pos}'
                )
                output.append((token, None))

        return ' '.join(f"{w}: {p}" if p else w for w, p in output)
        
    async def get_pronunciation(
        self, word: str, oxford_pos: str=None, treebank_pos: str=None
    ) -> dict:
        """
        oxford_pos: the part of speech (‘noun’, ‘verb’, ‘adjective’ etc.) 
                    of a word classified by Oxford Dictionary.

        treebank_pos: the part of speech (‘noun’, ‘verb’, ‘adjective’ etc.) 
                    of a word classified by Treebank.

        >>> import asyncio
        >>> loop = asyncio.new_event_loop()
        >>> app_id = os.getenv('OXFORD_DICTIONARY_APP_ID')
        >>> app_key = os.getenv('OXFORD_DICTIONARY_APP_KEY')
        >>> api_base_url = 'https://od-api.oxforddictionaries.com/api/v2'
        >>> dictionary = OxfordEngDict(
        ... api_base_url, app_id, app_key, dictionary_db_path='dictionary_test.db')

        # Test cache
        >>> print(dictionary.cache)
        CacheInfo(hits=0, misses=0, currsets=0)
        >>> loop.run_until_complete(dictionary.get_pronunciation('book'))
        {'pronunciation': 'bʊk', 'error': None}
        >>> print(dictionary.cache)
        CacheInfo(hits=0, misses=1, currsets=1)
        >>> loop.run_until_complete(dictionary.get_pronunciation('book'))
        {'pronunciation': 'bʊk', 'error': None}
        >>> print(dictionary.cache)
        CacheInfo(hits=1, misses=1, currsets=1)
        >>> print(dictionary.num_api_requests)
        1
        >>> loop.run_until_complete(dictionary.get_pronunciation('a', oxford_pos='determiner'))
        {'pronunciation': 'ə', 'error': None}
        >>> print(dictionary.cache)
        CacheInfo(hits=1, misses=2, currsets=2)
        >>> print(dictionary.num_api_requests)
        2
        >>> loop.run_until_complete(dictionary.get_pronunciation('a', oxford_pos='determiner'))
        {'pronunciation': 'ə', 'error': None}
        >>> print(dictionary.cache)
        CacheInfo(hits=2, misses=2, currsets=2)
        >>> print(dictionary.num_api_requests)
        2

        # Get pronunciation without specifying the part of speech.
        >>> loop.run_until_complete(dictionary.get_pronunciation('so'))
        {'pronunciation': 'səʊ', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation('is'))
        {'pronunciation': 'ɪz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation('a'))
        {'pronunciation': 'eɪ', 'error': None}

        # Get pronunciation when the part of speech of a word known.
        >>> loop.run_until_complete(dictionary.get_pronunciation('a', oxford_pos='determiner'))
        {'pronunciation': 'ə', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation('works', oxford_pos='verb'))
        {'pronunciation': None, 'error': <ErrorCodes.LEMMA_MISSING_PRONUNCIATION: 'lemma_missing_pronunciation'>}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'looking', oxford_pos='verb', treebank_pos='VBG'))
        {'pronunciation': 'lʊkɪŋ', 'error': None}

        # Final 'ed' is pronounced /t/ after a voiceless consonant. 
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'coughed', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'kɒft', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'stopped', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'stɒpt', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'liked', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'lʌɪkt', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'crossed', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'krɒst', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'released', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'rɪˈliːst', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'reached', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'riːtʃt', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'washed', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'wɒʃt', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'bathed', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'bɑːθt', 'error': None}

        # Final 'ed' is pronounced /d/ after a voiced consonant or vowel.
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'robbed', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'rɒbd', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'saved', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'seɪvd', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'seized', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'siːzd', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'called', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'kɔːld', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'planned', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'pland', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'occurred', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'əˈkəːd', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'managed', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'ˈmanɪdʒd', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'played', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'pleɪd', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'tried', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'trʌɪd', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'studied', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'ˈstʌdid', 'error': None}

        # Final 'ed' is pronounced /id/ after the letters t and d.
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'wanted', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'wɒntid', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'hated', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'heɪtid', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'counted', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'kaʊntid', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'started', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'stɑːtid', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'needed', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'niːdid', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'loaded', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'ləʊdid', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'folded', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'fəʊldid', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'added', oxford_pos='verb', treebank_pos='VBD'))
        {'pronunciation': 'adid', 'error': None}

        # Final 's/es' is pronounced /s/ after a voiceless consonant
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'tapes', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'teɪps', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'streets', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'striːts', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'parks', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'pɑːks', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'chiefs', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'tʃiːfs', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'myths', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'mɪθs', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'leaves', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'liːfs', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'grips', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'ɡrɪps', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'writes', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'rʌɪts', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'takes', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'teɪks', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'sniffs', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'snɪfs', 'error': None}

        # Final 's/es' is pronounced /z/ after a voiced consonant or vowel.
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'ribs', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'rɪbz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'kids', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'kɪdz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'legs', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'lɛɡz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'clothes', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'kləʊ(ð)z', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'girls', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'ɡəːlz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'games', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'ɡeɪmz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'cars', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'kɑːz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'boys', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'bɔɪz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'pies', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'pʌɪz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'cows', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'kaʊz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'cities', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'ˈsɪtiz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'robs', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'rɒbz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'reads', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'riːdz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'digs', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'dɪɡz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'saves', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'seɪvz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'falls', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'fɔːlz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'plans', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'planz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'swims', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'swɪmz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'offers', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'ˈɒfəz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'plays', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'pleɪz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'cries', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'krʌɪz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'goes', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'ɡəʊz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'copies', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'ˈkɒpiz', 'error': None}

        # Final 's/es' is pronounced /iz/ after the letters s, z, x, ch, tch,
        # ge, dge, sh
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'pieces', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'piːsiz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'roses', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'rəʊziz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'prizes', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'prʌɪziz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'boxes', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'bɒksiz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'coaches', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'kəʊtʃiz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'bridges', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'brɪdʒiz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'dishes', oxford_pos='noun', treebank_pos='NNS'))
        {'pronunciation': 'dɪʃiz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'kisses', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'kɪsiz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'loses', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'luːziz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'relaxes', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'rɪˈlaksiz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'catches', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'katʃiz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'judges', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'dʒʌdʒiz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'manages', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'ˈmanɪdʒiz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'flashes', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'flaʃiz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'washes', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'wɒʃiz', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'rouges', oxford_pos='verb', treebank_pos='VBZ'))
        {'pronunciation': 'ruːʒiz', 'error': None}

        # Comparative and superlative adjectives. 
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'bigger', oxford_pos='adjective', treebank_pos='JJR'))
        {'pronunciation': 'bɪɡə', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'happier', oxford_pos='adjective', treebank_pos='JJR'))
        {'pronunciation': 'ˈhapiə', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'biggest', oxford_pos='adjective', treebank_pos='JJS'))
        {'pronunciation': 'bɪɡəst', 'error': None}
        >>> loop.run_until_complete(dictionary.get_pronunciation(
        ... 'happiest', oxford_pos='adjective', treebank_pos='JJS'))
        {'pronunciation': 'ˈhapiəst', 'error': None}

        # Get pronunciation of an unexisting word.
        >>> loop.run_until_complete(dictionary.get_pronunciation('0.1a'))
        {'pronunciation': None, 'error': <ErrorCodes.CANNOT_FIND_IN_DICT: 'cannot_find_in_dict'>}

        # Do clean up after running tests.
        >>> loop.run_until_complete(dictionary.close())
        >>> loop.close()
        >>> import os
        >>> os.remove('dictionary_test.db')
        """
        cache_key = f'pronunciation__{word}'
        if oxford_pos:
            cache_key += f'__{oxford_pos}'

        # Try to get the value from the cache.
        result = {
            'pronunciation': self.cache.get(key=cache_key),
            'error': None
        }

        if result['pronunciation'] is not self.cache.missing_value_sentinel:
            return result

        # Unset missing value sentinel.
        result['pronunciation'] = None

        # The value is NOT in the CACHE. Try to get it from the Oxford Dict. 
        url = f'{self.api_base_url}/entries/{self.source_lang}-gb/{word}'
        query_params = {'fields': 'pronunciations'}
        if oxford_pos:
            query_params['lexicalCategory'] = oxford_pos
        query = urllib.parse.urlencode(query_params)

        http_request = self.form_http_request(f'{url}?{query}')
        response = await self.fetch_response(http_request)

        if response['is_success']:
            try:
                pronunciations = None
                _results = response['response']['results']
                for _res in _results:
                    lexical_entries = _res['lexicalEntries']
                    if 'pronunciations' in lexical_entries[0]:
                        pronunciations = lexical_entries[0]['pronunciations']
                        break

                    entries = lexical_entries[0]['entries']
                    if 'pronunciations' in entries[0]:
                        pronunciations = entries[0]['pronunciations']
                        break

                if pronunciations is not None:
                    pronunciation = pronunciations[0]['phoneticSpelling']
                    self.cache.set(key=cache_key, value=pronunciation)
                    result['pronunciation'] = pronunciation
                else:
                    logger.exception(f'Response: {response}')
                    result['error'] = 'Pronunciation is missing'

            except Exception as err:
                logger.exception(f'Error: {err}, Response: {response}')
                result['error'] = str(err)

        else:
            result['error'] = response['error']

        # Oxford API returned pronunciation.
        if result['pronunciation'] is not None:
            return result

        # If Oxford API could not find an entry in the dictionary.
        # Try to get its lemma.
        if result['error'] is ErrorCodes.CANNOT_FIND_IN_DICT:
            lemma = None

            # Get the lemma by specifying Oxford part-of-speech tag.
            _res = await self.get_lemmas(word, oxford_pos=oxford_pos)
            lemmas, err = _res['lemmas'], _res['error']
            lemma = lemmas[0] if lemmas else None

            # If the lemma still empty, try to get it without specifying
            # part-of-speech tag.
            if not lemma and err is ErrorCodes.EMPTY_RESULT:
                _res = await self.get_lemmas(word)
                lemmas, err = _res['lemmas'], _res['error']
                lemma = lemmas[0] if lemmas else None

            if not lemma:
                return result

            lemma_pronunciation = None
            if lemma and treebank_pos is not None:
                res = await self.get_pronunciation(lemma)
                if res['pronunciation'] is None:
                    return result

                lemma_pronunciation = res['pronunciation'] 

                if lemma.lower() == word.lower():
                    result['pronunciation'] = lemma_pronunciation
                    result['error'] = None
                    return result

                # JJR adjective, comparative ‘bigger’
                if treebank_pos == 'JJR':
                    pronunciation = lemma_pronunciation + 'ə'
                    self.cache.set(key=cache_key, value=pronunciation)
                    result['pronunciation'] = pronunciation
                    result['error'] = None
                    return result

                # JJS adjective, superlative ‘biggest’
                if treebank_pos == 'JJS':
                    pronunciation = lemma_pronunciation + 'əst'
                    self.cache.set(key=cache_key, value=pronunciation)
                    result['pronunciation'] = pronunciation
                    result['error'] = None
                    return result

                # VBG verb, gerund/present participle: taking
                if treebank_pos == 'VBG':
                    pronunciation = lemma_pronunciation + 'ɪŋ'
                    self.cache.set(key=cache_key, value=pronunciation)
                    result['pronunciation'] = pronunciation
                    result['error'] = None
                    return result

                # VBD verb, past tense took
                # The final –ed ending has three different 
                # pronunciations: /t/, /d/, and /ed/
                if treebank_pos == 'VBD' and word[-2:] == 'ed':
                    # Final 'ed' is pronounced /t/ after a voiceless consonant. 
                    if (
                        lemma_pronunciation[-1] in (
                            'f', 'θ', 's', 'ʃ', 'h', 'p', 'k', ) 
                        or
                        lemma_pronunciation[-2:] in ('tʃ')
                    ):
                        pronunciation = lemma_pronunciation + 't'
                        self.cache.set(key=cache_key, value=pronunciation)
                        result['pronunciation'] = pronunciation
                        result['error'] = None
                        return result

                    # Final 'ed' is pronounced /d/ after a voiced consonant or
                    # vowel
                    if (
                        lemma_pronunciation[-1] in (
                            'v', 'ð', 'z', 'ʒ', 'b', 'g', 'w', 'r', 'j',
                            'l', 'm', 'n', 'ŋ',
                            'ʌ', 'ɪ', 'ʊ', 'e', 'a', 'ɒ', 'i', 'o', 'u', 'y'
                        ) 
                        or
                        lemma_pronunciation[-2:] in (
                            'dʒ',
                            'iː', 'uː', 'ɪə', 'ʊə', 'eɪ', 'əʊ', 'ɔɪ', 'ɔː',
                            'aʊ', 'ʌɪ', 'ɑː', 'əː'
                        )
                    ):
                        pronunciation = lemma_pronunciation + 'd'
                        self.cache.set(key=cache_key, value=pronunciation)
                        result['pronunciation'] = pronunciation
                        result['error'] = None
                        return result

                    # Final 'ed' is pronounced /id/ after the letters t and d.
                    if lemma_pronunciation[-1] in ( 't', 'd'):
                        pronunciation = lemma_pronunciation + 'id'
                        self.cache.set(key=cache_key, value=pronunciation)
                        result['pronunciation'] = pronunciation
                        result['error'] = None
                        return result

                # VBZ verb, 3rd person sing. present takes
                # NNS noun plural ‘desks’
                if treebank_pos in ('NNS', 'VBZ'):
                    # Final –s is pronounced /s/ after voiceless sounds. 
                    if (
                        lemma_pronunciation[-1] in (
                            'f', 'θ', 'h', 'p', 'k', 't'
                        ) 
                    ):
                        pronunciation = lemma_pronunciation + 's'
                        self.cache.set(key=cache_key, value=pronunciation)
                        result['pronunciation'] = pronunciation
                        result['error'] = None
                        return result

                    # Final 's/es' is pronounced /z/ after a voiced consonant or
                    # vowel
                    if (
                        lemma_pronunciation[-1] in (
                            'v', 'ð', 'b', 'ɡ', 'w', 'r', 'j',
                            'l', 'm', 'n', 'ŋ', 'd',
                            'ʌ', 'ɪ', 'ʊ', 'e', 'a', 'ɒ', 'i', 'o', 'u', 'y',
                            'ə'
                        ) 
                        or
                        lemma_pronunciation[-2:] in (
                            'iː', 'uː', 'ɪə', 'ʊə', 'eɪ', 'əʊ', 'ɔɪ', 'ɔː',
                            'aʊ', 'ʌɪ', 'ɑː', 'əː'
                        )
                    ):
                        pronunciation = lemma_pronunciation + 'z'
                        self.cache.set(key=cache_key, value=pronunciation)
                        result['pronunciation'] = pronunciation
                        result['error'] = None
                        return result

                    # Final 's/es' is pronounced /iz/ after the 
                    # letters s, z, x, ch, tch, ge, dge, sh
                    if (
                        lemma_pronunciation[-1] in ('s', 'z', 'ʃ', 'ʒ') 
                        or
                        lemma_pronunciation[-2:] in ('tʃ', 'dʒ')
                    ):
                        pronunciation = lemma_pronunciation + 'iz'
                        self.cache.set(key=cache_key, value=pronunciation)
                        result['pronunciation'] = pronunciation
                        result['error'] = None
                        return result

            # If we got here, it means we have a missing case for the 
            # correct pronunciation. We will explicitly return an error
            # result to indicate this.
            result = {
                'pronunciation': None,
                'error': self.error_codes.LEMMA_MISSING_PRONUNCIATION
            }
            return result

        return result

    def form_http_request(self, url, method='get', headers=None):
        _headers = {
            'app_id': self.app_id or '',
            'app_key': self.app_key or ''
        }
        if headers is not None:
            _headers.update(headers)

        http_request = HTTPRequest(
            url, method=method.upper(), headers=_headers,
            connect_timeout=20, request_timeout=20
        )
        return http_request

    async def fetch_response(self, http_request: HTTPRequest):
        self.num_api_requests += 1
        result = {'is_success': None, 'error': None, 'response': None}

        try:
            response: HTTPResponse = await self.async_http_client.fetch(
                http_request,
                # argument only affects the `HTTPError` raised 
                # when a non-200 response code is
                # used, instead of suppressing all errors.
                raise_error=False
            )
        except Exception as err:
            logger.exception(err)
            result['is_success'] = False
            result['error'] = str(err)
            return result

        if response.code == 200:
            result['is_success'] = True
            result['response'] = json.loads(response.body)

        elif response.code == 404:
            result['is_success'] = False
            result['error'] = self.error_codes.CANNOT_FIND_IN_DICT

        else:
            result['is_success'] = False
            result['error'] = response.body

        if not result['is_success']:
            logger.error(
                f'Http request url: {http_request.url}, '
                f'result: {result}'
            )

        return result

    def _map_treebank_pos_into_oxford_pos(self, treebank_tag):
        # CC coordinating conjunction
        if treebank_tag in ['CC']:
            return "conjunction"

        # DT determiner
        # WDT wh-determiner which
        if treebank_tag in ['DT', 'WDT']:
            return "determiner"

        # JJ adjective ‘big’
        # JJR adjective, comparative ‘bigger’
        # JJS adjective, superlative ‘biggest’
        if treebank_tag in ['JJ', 'JJR', 'JJS']:
            return "adjective"

        # IN preposition/subordinating conjunction
        if treebank_tag in ['IN']:
            return "preposition"

        # NN noun, singular ‘desk’
        # NNS noun plural ‘desks’
        if treebank_tag in ['NN', 'NNS']:
            return "noun"

        # VB  verb, base form take
        # VBD verb, past tense took
        # VBG verb, gerund/present participle taking
        # VBN verb, past participle taken
        # VBP verb, sing. present, non-3d take
        # VBZ verb, 3rd person sing. present takes
        # MD modal could, will
        if treebank_tag in ['VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ', 'MD']:
            return 'verb'

        # RB adverb very, silently,
        # RBR adverb, comparative better
        # RBS adverb, superlative best
        # WRB wh-abverb where, when
        if treebank_tag in ['RB', 'RBR', 'RBS', 'WRB']:
            return 'adverb'

        # WP wh-pronoun who, what
        # WP$ possessive wh-pronoun whose
        # PRP$ possessive pronoun my, his, hers
        if treebank_tag in ['WP', 'WP$', 'PRP$']:
            return 'pronoun'

        # CD cardinal digit
        # EX existential there (like: “there is” … think of it like “there exists”)
        # FW foreign word
        # LS list marker 1)
        # NNP proper noun, singular ‘Harrison’
        # NNPS proper noun, plural ‘Americans’
        # PDT predeterminer ‘all the kids’
        # POS possessive ending parent’s
        # PRP personal pronoun I, he, she
        # RP particle give up
        # TO, to go ‘to’ the store.
        # UH interjection, errrrrrrrm
        if treebank_tag in [
            'CD', 'EX', 'FW', 'LS', 'NNP', 'NNPS',
            'PDT', 'POS', 'PRP', 'RP', 'TO', 'UH']:
            return None

        raise Exception(f'Unknown treebank tag: {treebank_tag}')


class Cache:

    def __init__(self, lang, dictionary_db_path):
        self.hits = 0
        self.misses = 0
        self.currsets = 0
        self.missing_value_sentinel = object()
        self.db_conn = sqlite3.connect(
            dictionary_db_path,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        self.db_conn.row_factory = sqlite3.Row
        self.db_cursor = self.db_conn.cursor()
        self.lang = lang
        self.db_name = 'dictionary_cache'
        self.setup_cache_table()

    def setup_cache_table(self):
        self.db_cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='{db_name}';
        """.format(db_name=self.db_name))
        cache_table = self.db_cursor.fetchone()
        if cache_table is None:
            with open('sql/dictionary_cache.sql') as fh:
                cache_table = fh.read()
            self.db_cursor.execute(cache_table)
            self.db_conn.commit()

    async def close(self):
        self.db_cursor.close()
        self.db_conn.close()

    def get(self, key):
        self.db_cursor.execute(
            'SELECT * '
            'FROM {db_name} '
            'WHERE lang=? and key=?'.format(db_name=self.db_name),
            (self.lang, key)
        )
        res = self.db_cursor.fetchone()
        if not res:
            self.misses += 1
            return self.missing_value_sentinel

        self.hits += 1
        return json.loads(res['value'])['value']

    def set(self, key, value):
        with self.db_conn:
            self.db_cursor.execute(
                'INSERT INTO {db_name}(lang, key, value) '
                'VALUES '
                '(:lang, :key, :value)'.format(db_name=self.db_name),
                {
                    'lang': self.lang,
                    'key': key,
                    'value': json.dumps({'value': value})
                }
            )
        self.currsets += 1

    def __str__(self):
        return (
            f'CacheInfo(hits={self.hits}, misses={self.misses}, '
            f'currsets={self.currsets})'
        )


if __name__ == '__main__':
    # Run doctests with the following command:
    # PYTHONPATH='.' python3.6 src/dictionary.py
    # Tests all methods
    doctest.testmod(verbose=False)
    # Tests a single method
    #doctest.run_docstring_examples(OxfordEngDict.get_pronunciation, globals())
