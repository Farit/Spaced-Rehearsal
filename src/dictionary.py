import logging
import json
import string
import os

from tornado.httpclient import (
    AsyncHTTPClient, HTTPRequest, HTTPResponse, HTTPError
)

from src.config import ConfigAdapter


logger = logging.getLogger(__name__)


class Dictionary:

    def __init__(self):
        self.oxford_dict = OxfordDictionary()

    async def get_word_phonetic_spelling(self, word, source_lang='en'):
        phonetic_spelling = None
        normalized_word = self._normalize_word(word)

        logger.info(
            f'Get word phonetic spelling: word={word}. '
            f'Trying oxford dictionary'
        )
        if self.oxford_dict.is_in_service:
            phonetic_spelling = await self.oxford_dict.get_word_phonetic_spelling(
                word=normalized_word,
                source_lang=source_lang
            )
        else:
            logger.info(
                f'Get word phonetic spelling: word={word}. '
                f'Oxford dictionary is out of service.'
            )

        return phonetic_spelling

    @staticmethod
    def _normalize_word(word):
        normalized_word = word.lower().strip()
        normalized_word = normalized_word.strip(string.punctuation)
        return normalized_word


class OxfordDictionary:

    def __init__(self):
        self.config = ConfigAdapter(filename='config.cfg')
        self.api_base_url = self.config['dictionary'].get(
            'oxford_dict_api_base_url'
        )
        self.app_id = os.getenv('OXFORD_DICTIONARY_APP_ID')
        self.app_key = os.getenv('OXFORD_DICTIONARY_APP_KEY')
        self.async_http_client = AsyncHTTPClient()

    @property
    def is_in_service(self):
        return (
            bool(self.app_id) and bool(self.app_key) and bool(self.api_base_url)
        )

    async def get_word_phonetic_spelling(
            self, word, source_lang, is_lemmatize=False
    ):
        logger.info(
            f'Get word phonetic spelling: word={word}, '
            f'source_lang={source_lang}, '
            f'is_lemmatize={is_lemmatize}'
        )
        spelling = None
        try:
            if is_lemmatize:
                root_form = await self._retrieve_word_root_form(
                    word=word,
                    source_lang=source_lang
                )
                lexical_entries = root_form['results'][0]['lexicalEntries']
                inflections = lexical_entries[0]['inflectionOf']
                word = inflections[0]['id']

            word_info = await self._retrieve_info_for_a_given_word(
                word=word,
                source_lang=source_lang
            )
            lexical_entries = word_info['results'][0]['lexicalEntries']
            pronunciations = lexical_entries[0]['pronunciations']
            spelling = pronunciations[0]['phoneticSpelling']

        except EntryNotFound as err:
            if not is_lemmatize:
                logger.error(
                    f'Get word phonetic spelling: word={word}, err={err}. '
                    f'Trying lemmatization.'
                )
                spelling = await self.get_word_phonetic_spelling(
                    word=word,
                    source_lang=source_lang,
                    is_lemmatize=True
                )
            else:
                logger.error(
                    f'Get word phonetic spelling: word={word}, err={err}. '
                )

        except Exception as err:
            logger.exception(
                f'Get word phonetic spelling: word={word}, err={err}'
            )

        return spelling

    async def _retrieve_info_for_a_given_word(self, word, source_lang):
        word_id = word
        url = f'{self.api_base_url}/entries/{source_lang}/{word_id}'
        http_request = HTTPRequest(
            url,
            method='GET',
            headers={
                'app_id': self.app_id,
                'app_key': self.app_key
            }
        )
        response = await self._make_request(http_request)
        return response

    async def _retrieve_word_root_form(self, word, source_lang):
        word_id = word
        url = f'{self.api_base_url}/inflections/{source_lang}/{word_id}'
        http_request = HTTPRequest(
            url,
            method='GET',
            headers={
                'app_id': self.app_id,
                'app_key': self.app_key
            }
        )
        response = await self._make_request(http_request)
        return response

    async def _make_request(self, http_request: HTTPRequest):
        try:
            response: HTTPResponse = await self.async_http_client.fetch(
                http_request
            )
        except HTTPError as err:
            if err.code == 404:
                raise EntryNotFound(
                    code=404,
                    message=http_request.url,
                    response=err.response
                )
            raise err

        if response.code == 200:
            return json.loads(response.body)


class EntryNotFound(Exception):

    def __init__(self, code, message=None, response=None):
        self.code = code
        self.message = message
        self.response = response
        super(EntryNotFound, self).__init__(code, message, response)

    def __str__(self):
        return "Entry not found %d: %s" % (self.code, self.message)
