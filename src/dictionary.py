import enum
import logging
import json
import string
import os

from tornado.httpclient import (
    AsyncHTTPClient, HTTPRequest, HTTPResponse, HTTPError
)

logger = logging.getLogger(__name__)


class Dictionary:
    class Lang(enum.Enum):
        ENG = 'english'

    def __init__(self, lang: Lang, config):
        self.lang = lang
        self.config = config
        self.oxford_eng_dict = OxfordEngDictionary(config=config)

    async def get_text_phonetic_spelling(self, text):
        result = []
        spellings = {}

        for word in text.split():
            normalized_word = self._normalize_word(word)
            if normalized_word not in spellings:
                spelling = await self.get_word_phonetic_spelling(
                    normalized_word
                )
                spellings[normalized_word] = f'/{spelling}/'

            result.append((normalized_word, spellings[normalized_word]))

        return '   '.join(f'{word}: {spelling}' for word, spelling in result)

    async def get_word_phonetic_spelling(self, word):
        spelling = None
        log_prefix_msg = (
            f'Get word phonetic spelling: word={word}, '
            f'lang={self.lang.value}.'
        )

        if self.lang == self.Lang.ENG:
            logger.info(
                f'{log_prefix_msg} '
                f'Trying Oxford English Dictionary.'
            )

            if not self.oxford_eng_dict.is_in_service:
                logger.info(
                    f'{log_prefix_msg} '
                    f'Oxford English Dictionary is out of service.'
                )
                return spelling

            spelling = await self.oxford_eng_dict.get_word_phonetic_spelling(
                word=word,
                is_lemmatize=False
            )
            if not spelling:
                spelling = await self.oxford_eng_dict.get_word_phonetic_spelling(
                    word=word,
                    is_lemmatize=True
                )

        return spelling

    @staticmethod
    def _normalize_word(word):
        normalized_word = word.lower().strip()
        normalized_word = normalized_word.strip(string.punctuation)
        return normalized_word


class OxfordEngDictionary:
    """
    Docs: https://developer.oxforddictionaries.com/documentation
    """
    source_lang = 'en'

    def __init__(self, config):
        self.config = config
        self.api_base_url = self.config['dictionary'].get(
            'oxford_dict_api_base_url'
        )
        self.app_id = os.getenv('OXFORD_DICTIONARY_APP_ID')
        self.app_key = os.getenv('OXFORD_DICTIONARY_APP_KEY')
        self.async_http_client = AsyncHTTPClient()

    @property
    def is_in_service(self):
        return (
            bool(self.app_id) and
            bool(self.app_key) and
            bool(self.api_base_url)
        )

    async def get_word_phonetic_spelling(self, word, is_lemmatize=False):
        logger.info(
            f'Get word phonetic spelling: word={word}, '
            f'source_lang={self.source_lang}, '
            f'is_lemmatize={is_lemmatize}'
        )
        spelling = None
        try:
            if is_lemmatize:
                word = await self._retrieve_root_form(word=word)
            spelling = await self._retrieve_spelling(word=word)

        except EntryNotFound as err:
            logger.error(f'Get word phonetic spelling: word={word}, err={err}')

        return spelling

    async def _retrieve_spelling(self, word):
        word_id = word
        url = f'{self.api_base_url}/entries/{self.source_lang}/{word_id}'
        http_request = HTTPRequest(
            url,
            method='GET',
            headers={
                'app_id': self.app_id,
                'app_key': self.app_key
            }
        )
        response = await self._make_request(http_request)
        lexical_entries = response['results'][0]['lexicalEntries']
        pronunciations = lexical_entries[0]['pronunciations']
        spelling = pronunciations[0]['phoneticSpelling']
        return spelling

    async def _retrieve_root_form(self, word):
        word_id = word
        url = f'{self.api_base_url}/inflections/{self.source_lang}/{word_id}'
        http_request = HTTPRequest(
            url,
            method='GET',
            headers={
                'app_id': self.app_id,
                'app_key': self.app_key
            }
        )
        response = await self._make_request(http_request)
        lexical_entries = response['results'][0]['lexicalEntries']
        inflections = lexical_entries[0]['inflectionOf']
        word_root_form = inflections[0]['id']
        return word_root_form

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
