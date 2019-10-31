import enum
import logging

from abc import ABC, abstractmethod

from tornado.httpclient import AsyncHTTPClient

from src.dictionary.offline_dictionary import OfflineDict

logger = logging.getLogger(__name__)


class ErrorCodes(enum.Enum):
    EMPTY_RESULT = 'empty_result'
    CANNOT_FIND_IN_DICT = 'cannot_find_in_dict'
    LEMMA_MISSING_PRONUNCIATION = 'lemma_missing_pronunciation'


class DictionaryAbstract(ABC):
    error_codes = ErrorCodes

    def __init__(self, lang, dictionary_db_path):
        self.offline_dict: OfflineDict = OfflineDict(
            lang=lang,
            dictionary_db_path=dictionary_db_path
        )
        self.async_http_client: AsyncHTTPClient = AsyncHTTPClient()
        self.num_api_requests: int = 0

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
    async def get_word_pronunciation(self, word: str) -> dict:
        """
        Returns pronunciation of a word (e.g., book -> bʊk).

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
        await self.offline_dict.close()
