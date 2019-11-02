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

    async def _collect_data(self):
        data = {}
        data['question'] = await self.mediator.input_question()
        data['answer'] = await self.mediator.input_answer()

        data['source'] = await self.mediator.input_source()
        data['phonetic_transcription'] = (
            await self.mediator.input_phonetic_transcription(
                flashcard_answer=data['answer']
            )
        )
        data['explanation'] = await self.mediator.input_explanation()
        data['examples'] = await self.mediator.input_examples()
        return data


class EnglishRussianCreateAction(GeneralCreateAction):

    def __init__(self, mediator):
        super().__init__(mediator)
        self.async_http_client = AsyncHTTPClient()

    async def _collect_data(self):
        data = {}
        data['answer'] = await self.mediator.input_answer(label='English answer')

        rus_translation = None
        if data['answer']:
            rus_translation = await self.translate(data['answer'])

        data['question'] = await self.mediator.input_question(
            label='Russian question', pre_fill=rus_translation
        )

        data['source'] = await self.mediator.input_source()
        data['phonetic_transcription'] = (
            await self.mediator.input_phonetic_transcription(
                flashcard_answer=data['answer']
            )
        )
        data['explanation'] = await self.mediator.input_explanation()
        data['examples'] = await self.mediator.input_examples()
        return data

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
