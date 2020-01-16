import logging
import json
import string
import doctest
import urllib.parse

import nltk

from nltk.tokenize import word_tokenize
from tornado.httpclient import HTTPRequest, HTTPResponse
from src.dictionary.base import DictionaryAbstract

logger = logging.getLogger(__name__)


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
        res = {'is_success': True, 'error': None}

        url = f'{self.api_base_url}/lemmas/{self.source_lang}/book'
        http_request = self.form_http_request(url)
        response = await self.fetch_response(http_request)

        if not response['is_success']:
            res['is_success'] = False
            res['error'] = response['error']

        return res

    async def get_lemmas(
            self, word: str, oxford_pos: str = None, force: bool = False
    ) -> dict:
        """
        oxford_pos: the part of speech (‘noun’, ‘verb’, ‘adjective’ etc.)
                    of a word classified by Oxford Dictionary.
        """
        result = {
            'lemmas': self.offline_dict.get(
                key=word, field='lemmas', grammatical_feature=oxford_pos
            ),
            'error': None
        }

        if result['lemmas'] is self.offline_dict.missing_value_sentinel:
            result['lemmas'] = None

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
                    lex_result = response['results'][0]
                    for lexical_entry in lex_result['lexicalEntries']:
                        inflection = lexical_entry['inflectionOf']
                        root_form = inflection[0]['id']
                        lemmas.append(root_form)

                    self.offline_dict.set(
                        key=word,
                        value=lemmas,
                        field='lemmas',
                        grammatical_feature=oxford_pos
                    )
                    result['lemmas'] = lemmas

                else:
                    result['error'] = self.error_codes.EMPTY_RESULT
            else:
                result['error'] = response['error']

        if not result['lemmas']:
            logger.error(
                f'Http request url: {http_request.url}, '
                f'result: {result} '
                f'context: word={word}, oxford_pos={oxford_pos}, force={force}'
            )

        if not result['lemmas'] and oxford_pos is not None and force:
            # If the lemma still empty, try to get it without specifying
            # part-of-speech tag.
            result = await self.get_lemmas(word, oxford_pos=None, force=False)

        return result

    async def get_text_pronunciation(self, text: str) -> str:
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

            res = await self.get_word_pronunciation(
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

    async def get_word_pronunciation(
        self, word: str, oxford_pos: str = None, treebank_pos: str = None
    ) -> dict:
        """
        oxford_pos: the part of speech (‘noun’, ‘verb’, ‘adjective’ etc.)
                    of a word classified by Oxford Dictionary.

        treebank_pos: the part of speech (‘noun’, ‘verb’, ‘adjective’ etc.)
                    of a word classified by Treebank.
        """
        result = {
            'pronunciation': self.offline_dict.get(
                key=word, field='pronunciation', grammatical_feature=oxford_pos
            ),
            'error': None
        }

        if result['pronunciation'] is not self.offline_dict.missing_value_sentinel:
            return result

        result = {
            'pronunciation': self.offline_dict.get(
                key=word, field='pronunciation'
            ),
            'error': None
        }

        if result['pronunciation'] is not self.offline_dict.missing_value_sentinel:
            return result
        
        result['pronunciation'] = None

        result = await self._get_pronunciation(
            word=word, oxford_pos=oxford_pos
        )
        if result['pronunciation'] is not None:
            self.offline_dict.set(
                key=word, value=result['pronunciation'],
                field='pronunciation', grammatical_feature=oxford_pos
            )
            return result

        result = await self._get_pronunciation(word=word)
        if result['pronunciation'] is not None:
            self.offline_dict.set(
                key=word, value=result['pronunciation'],
                field='pronunciation'
            )
            return result

        # If Oxford API could not find an entry in the dictionary.
        # Try to get its lemma.
        if result['error'] is self.error_codes.CANNOT_FIND_IN_DICT:

            # Get the lemma by specifying Oxford part-of-speech tag.
            get_lemmas_res = await self.get_lemmas(
                word, oxford_pos=oxford_pos, force=True
            )
            if not get_lemmas_res['lemmas']:
                return result

            lemma = get_lemmas_res['lemmas'][0]
            lemma_pronunciation = None
            if lemma and treebank_pos is not None:
                res = await self.get_word_pronunciation(lemma)
                lemma_pronunciation = res['pronunciation']
                if lemma_pronunciation is None:
                    return result

                word_pronunciation = self._construct_compound_word_pronunciation(
                    word=word,
                    lemma=lemma,
                    lemma_pronunciation=lemma_pronunciation,
                    word_treebank_pos=treebank_pos
                )
                if word_pronunciation:
                    self.offline_dict.set(
                        key=word, value=word_pronunciation,
                        field='pronunciation', grammatical_feature=oxford_pos
                    )
                    result['pronunciation'] = word_pronunciation
                    result['error'] = None
                    return result

            # If we got here, it means we have a missing case for the
            # correct pronunciation. We will explicitly return an error
            # result to indicate this.
            result = {
                'pronunciation': None,
                'error': self.error_codes.LEMMA_MISSING_PRONUNCIATION
            }
            err_msg = (
                f'Get word pronunciation error: word={word}, lemma={lemma} '
                f'oxford_pos={oxford_pos}, treebank_pos={treebank_pos}, '
                f'result={result}, lemma_pronunciation={lemma_pronunciation}'
            )
            logger.error(err_msg)
            return result

        err_msg = (
            f'Get word pronunciation error: word={word}, '
            f'oxford_pos={oxford_pos}, treebank_pos={treebank_pos}, '
            f'result={result}'
        )
        logger.error(err_msg)
        return result

    async def _get_pronunciation(
        self, word: str, oxford_pos: str = None
    ) -> dict:
        word = word.lower()

        result = {
            'pronunciation': None,
            'error': None
        }

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
                    result['pronunciation'] = pronunciation
                else:
                    err_msg = (
                        f'Get pronunciation error: word={word}, '
                        f'oxford_pos={oxford_pos}, response={response}'
                    )
                    logger.error(err_msg)
                    result['error'] = self.error_codes.CANNOT_FIND_IN_DICT

            except Exception as err:
                err_msg = (
                    f'Get pronunciation error: word={word}, '
                    f'oxford_pos={oxford_pos}, '
                    f'error={err}, response={response}'
                )
                logger.exception(err_msg)
                result['error'] = str(err)

        else:
            err_msg = (
                f'Get pronunciation error: word={word}, '
                f'oxford_pos={oxford_pos}, response={response}'
            )
            logger.error(err_msg)
            result['error'] = response['error']

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

    @staticmethod
    def _construct_compound_word_pronunciation(
        word: str,
        lemma: str,
        lemma_pronunciation: str,
        word_treebank_pos: str
    ):
        if lemma.lower() == word.lower():
            return lemma_pronunciation

        # JJR adjective, comparative ‘bigger’
        if word_treebank_pos == 'JJR':
            return lemma_pronunciation + 'ə'

        # JJS adjective, superlative ‘biggest’
        if word_treebank_pos == 'JJS':
            return lemma_pronunciation + 'əst'

        # VBG verb, gerund/present participle: taking
        if word_treebank_pos == 'VBG':
            return lemma_pronunciation + 'ɪŋ'

        # VBD verb, past tense took
        # VBN verb, past participle taken
        # The final –ed ending has three different
        # pronunciations: /t/, /d/, and /ed/
        if word_treebank_pos in ['VBD', 'VBN'] and word[-2:] == 'ed':
            # Final 'ed' is pronounced /t/ after a voiceless consonant.
            if (
                lemma_pronunciation[-1] in (
                    'f', 'θ', 's', 'ʃ', 'h', 'p', 'k')
                or
                lemma_pronunciation[-2:] in ('tʃ')
            ):
                return lemma_pronunciation + 't'

            # Final 'ed' is pronounced /d/ after a voiced consonant or
            # vowel
            if (
                lemma_pronunciation[-1] in (
                    'v', 'ð', 'z', 'ʒ', 'b', 'g', 'w', 'r', 'j',
                    'l', 'm', 'n', 'ŋ',
                    'ʌ', 'ɪ', 'ʊ', 'e', 'a', 'ɒ', 'i', 'o', 'u', 'y', 'ə'
                )
                or
                lemma_pronunciation[-2:] in (
                    'dʒ',
                    'iː', 'uː', 'ɪə', 'ʊə', 'eɪ', 'əʊ', 'ɔɪ', 'ɔː',
                    'aʊ', 'ʌɪ', 'ɑː', 'əː', 'ɛː'
                )
            ):
                return lemma_pronunciation + 'd'

            # Final 'ed' is pronounced /id/ after the letters t and d.
            if lemma_pronunciation[-1] in ('t', 'd'):
                return lemma_pronunciation + 'id'

        # VBZ verb, 3rd person sing. present takes
        # NNS noun plural ‘desks’
        if word_treebank_pos in ('NNS', 'VBZ'):
            # Final –s is pronounced /s/ after voiceless sounds.
            if (
                lemma_pronunciation[-1] in (
                    'f', 'θ', 'h', 'p', 'k', 't'
                )
            ):
                return lemma_pronunciation + 's'

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
                    'aʊ', 'ʌɪ', 'ɑː', 'əː', 'ɛː'
                )
            ):
                return lemma_pronunciation + 'z'

            # Final 's/es' is pronounced /iz/ after the
            # letters s, z, x, ch, tch, ge, dge, sh
            if (
                lemma_pronunciation[-1] in ('s', 'z', 'ʃ', 'ʒ')
                or
                lemma_pronunciation[-2:] in ('tʃ', 'dʒ')
            ):
                return lemma_pronunciation + 'iz'

    @staticmethod
    def _map_treebank_pos_into_oxford_pos(treebank_tag):
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
        # PRP personal pronoun I, he, she
        if treebank_tag in ['WP', 'WP$', 'PRP$', 'PRP']:
            return 'pronoun'

        # CD cardinal digit
        # EX existential there
        #    (like: “there is” … think of it like “there exists”)
        # FW foreign word
        # LS list marker 1)
        # NNP proper noun, singular ‘Harrison’
        # NNPS proper noun, plural ‘Americans’
        # PDT predeterminer ‘all the kids’
        # POS possessive ending parent’s
        # RP particle give up
        # TO, to go ‘to’ the store.
        # UH interjection, errrrrrrrm
        if treebank_tag in [
            'CD', 'EX', 'FW', 'LS', 'NNP', 'NNPS',
            'PDT', 'POS', 'RP', 'TO', 'UH'
        ]:
            return None

        raise Exception(f'Unknown treebank tag: {treebank_tag}')


if __name__ == '__main__':
    # Run doctests with the following command:
    # PYTHONPATH='.' python3.6 src/dictionary.py
    # Tests all methods
    doctest.testmod(verbose=False)
    # Tests a single method
    # doctest.run_docstring_examples(OxfordEngDict.get_pronunciation, globals())
