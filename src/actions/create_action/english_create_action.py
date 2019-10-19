import os
import json
import logging
import urllib.parse


from src.flashcard import Flashcard
from src.actions.create_action.general_create_action import (
    GeneralCreateAction
)

from tornado.httpclient import (
    AsyncHTTPClient, HTTPRequest, HTTPResponse
)

logger = logging.getLogger(__name__)


class EnglishCreateAction(GeneralCreateAction):

    async def _create_flashcard(self):
        question = await self.mediator.input_question()
        answer = await self.mediator.input_answer()
        source = await self.mediator.input_source()
        phonetic_transcription = (
            await self.mediator.input_phonetic_transcription(
                flashcard_answer=answer
            )
        )
        explanation = await self.mediator.input_explanation()
        examples = await self.mediator.input_examples()

        flashcard: Flashcard = Flashcard.create(
            user_id=self.mediator.get_user_id(),
            flashcard_type=self.mediator.name(),
            question=question,
            answer=answer,
            source=source,
            phonetic_transcription=phonetic_transcription,
            explanation=explanation,
            examples=examples
        )
        return flashcard


class EnglishRussianCreateAction(GeneralCreateAction):

    def __init__(self, mediator):
        super().__init__(mediator)
        self.async_http_client = AsyncHTTPClient()

    async def _create_flashcard(self):
        answer = await self.mediator.input_answer(label='English answer')
        rus_translation = await self.translate(answer)
        question = await self.mediator.input_question(
            label='Russian question', pre_fill=rus_translation
        )
        source = await self.mediator.input_source()
        phonetic_transcription = (
            await self.mediator.input_phonetic_transcription(
                flashcard_answer=answer
            )
        )
        explanation = await self.mediator.input_explanation()
        examples = await self.mediator.input_examples()

        flashcard: Flashcard = Flashcard.create(
            user_id=self.mediator.get_user_id(),
            flashcard_type=self.mediator.name(),
            question=question,
            answer=answer,
            source=source,
            phonetic_transcription=phonetic_transcription,
            explanation=explanation,
            examples=examples
        )
        return flashcard

    async def translate(self, text):
        url = 'https://translate.yandex.net/api/v1.5/tr.json/translate'
        api_key = os.getenv('YANDEX_TRANSLATE_API_KEY')
        params = urllib.parse.urlencode({
            'key': api_key,
            'text': text,
            'lang': 'en-ru'
        })
        data = {}

        http_request = HTTPRequest(
            f'{url}?{params}',
            method='POST',
            body=json.dumps(data)
        )

        try:
            response: HTTPResponse = await self.async_http_client.fetch(
                http_request,
                # argument only affects the `HTTPError` raised 
                # when a non-200 response code is
                # used, instead of suppressing all errors.
                raise_error=False
            )
        except Exception as err:
            logger.exception(f'YaTranslate error: {err}')
            return None

        if response.code == 200:
            try:
                data = json.loads(response.body)
                if data['code'] == 200:
                    return data['text'][0]
            except Exception as err:
                logger.exception(f'YaTranslate error: {err}')

        logger.error(f'YaTranslate error: {response.body}')
