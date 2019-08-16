import enum
import logging
import json
import string
import socket
import os
import doctest
import sqlite3

from abc import ABC, abstractmethod

from tornado.httpclient import (
    AsyncHTTPClient, HTTPRequest, HTTPResponse, HTTPError
)

logger = logging.getLogger(__name__)


class ErrorCodes(enum.Enum):
    CANNOT_FIND_IN_DICT = 'cannot_find_in_dict'


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
    async def get_lemmas(self, word: str) -> dict:
        """
        Returns the possible lemmas ("root" forms) for a given inflected word.
        (e.g., swimming -> swim).
        Lemma is a general term for any headword, phrase, or other form
        that can be looked up in a dictionary.
        An inflection is a change in the form of a word to express a 
        grammatical function such as tense, mood, purson, number, case or 
        gender. (e.g., 'boxes' is an inflected form of 'box')

        Returns on success:
            {'lemmas': <lemmas>, 'error': None}
        Otherwise:
            {'lemmas': None, 'error': <error>}
        """
        pass

    @abstractmethod
    async def get_pronunciation(self, word: str) -> dict:
        """
        Returns pronunciation of a word (e.g., book -> bʊk)

        Returns on success:
            {'pronunciation': <pronunciation>, 'error': None}
        Otherwise:
            {'pronunciation': None, 'error': <error>}
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

    async def get_lemmas(self, word: str) -> dict:
        """
        >>> import asyncio
        >>> loop = asyncio.new_event_loop()
        >>> app_id = os.getenv('OXFORD_DICTIONARY_APP_ID')
        >>> app_key = os.getenv('OXFORD_DICTIONARY_APP_KEY')
        >>> api_base_url = 'https://od-api.oxforddictionaries.com/api/v2'
        >>> dictionary = OxfordEngDict(
        ... api_base_url, app_id, app_key, dictionary_db_path='dictionary_test.db')
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
        >>> loop.run_until_complete(dictionary.get_lemmas('aaabbbccc'))
        {'lemmas': None, 'error': <ErrorCodes.CANNOT_FIND_IN_DICT: 'cannot_find_in_dict'>}
        >>> loop.run_until_complete(dictionary.close())
        >>> loop.close()
        >>> import os
        >>> os.remove('dictionary_test.db')
        """
        cache_key = f'lemmas__{word}'
        result = {
            'lemmas': self.cache.get(key=cache_key),
            'error': None
        }

        if result['lemmas'] is self.cache.missing_value_sentinel:
            url = f'{self.api_base_url}/lemmas/{self.source_lang}/{word}'
            http_request = self.form_http_request(url)
            response = await self.fetch_response(http_request)

            if response['is_success']:
                response = response['response']
                lemmas = []
                for lexical_entry in response['results'][0]['lexicalEntries']:
                    inflection = lexical_entry['inflectionOf']
                    root_form = inflection[0]['id']
                    lemmas.append(root_form)

                self.cache.set(key=cache_key, value=lemmas)
                result['lemmas'] = lemmas

            else:
                result['lemmas'] = None
                result['error'] = response['error']

        return result

    async def get_pronunciation(self, word: str) -> dict: 
        """
        >>> import asyncio
        >>> loop = asyncio.new_event_loop()
        >>> app_id = os.getenv('OXFORD_DICTIONARY_APP_ID')
        >>> app_key = os.getenv('OXFORD_DICTIONARY_APP_KEY')
        >>> api_base_url = 'https://od-api.oxforddictionaries.com/api/v2'
        >>> dictionary = OxfordEngDict(
        ... api_base_url, app_id, app_key, dictionary_db_path='dictionary_test.db')
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
        >>> loop.run_until_complete(dictionary.get_pronunciation('0.1a'))
        {'pronunciation': None, 'error': <ErrorCodes.CANNOT_FIND_IN_DICT: 'cannot_find_in_dict'>}
        >>> loop.run_until_complete(dictionary.get_pronunciation('so'))
        {'pronunciation': 'səʊ', 'error': None}
        >>> loop.run_until_complete(dictionary.close())
        >>> loop.close()
        >>> import os
        >>> os.remove('dictionary_test.db')
        """
        cache_key = f'pronunciation__{word}'
        result = {
            'pronunciation': self.cache.get(key=cache_key),
            'error': None
        }

        if result['pronunciation'] is self.cache.missing_value_sentinel:
            url = f'{self.api_base_url}/entries/{self.source_lang}-gb/{word}'
            http_request = self.form_http_request(url)
            response = await self.fetch_response(http_request)

            if response['is_success']:
                try:
                    response = response['response']
                    lexical_entries = response['results'][0]['lexicalEntries']
                    try:
                        pronunciations = lexical_entries[0]['pronunciations']
                    except:
                        entries = lexical_entries[0]['entries']
                        pronunciations = entries[0]['pronunciations']

                    pronunciation = pronunciations[0]['phoneticSpelling']

                    self.cache.set(key=cache_key, value=pronunciation)
                    result['pronunciation'] = pronunciation

                except Exception as err:
                    logger.exception(f'Error: {err}, Response: {response}')
                    result['pronunciation'] = None
                    result['error'] = str(err)

            else:
                result['pronunciation'] = None
                result['error'] = response['error']

        return result

    def form_http_request(self, url, method='get', headers=None):
        _headers = {
            'app_id': self.app_id,
            'app_key': self.app_key
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
            logger.error(result)

        return result


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
    doctest.testmod(verbose=True)
