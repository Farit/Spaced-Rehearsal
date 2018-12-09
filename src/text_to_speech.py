import os
import json
import enum
import logging
import urllib.parse
import xml.sax.saxutils as xml_sax_utils

from tornado.httpclient import (
    AsyncHTTPClient, HTTPRequest, HTTPResponse, HTTPError
)

logger = logging.getLogger(__name__)


class TextToSpeech:
    class Lang(enum.Enum):
        ENG = 'english'

    def __init__(self, lang: Lang, config):
        self.lang = lang
        self.config = config
        self.ibm_eng_tts = IbmEngTextToSpeech(config)

    async def synthesize_audio(self, text):
        if self.lang == self.Lang.ENG:
            audio_file = await self.ibm_eng_tts.synthesize_audio(text)
            return audio_file


class IbmEngTextToSpeech:
    """
    Docs: https://cloud.ibm.com/docs/services/text-to-speech/getting-started.html#gettingStarted
    """

    def __init__(self, config):
        self.config = config
        self.api_base_url = self.config['text_to_speech'].get('ibm_api_url')
        self.auth_username = os.getenv('IBM_TEXT_TO_SPEECH_AUTH_USERNAME')
        self.auth_password = os.getenv('IBM_TEXT_TO_SPEECH_AUTH_PASSWORD')
        self.http_client = AsyncHTTPClient()

    async def synthesize_audio(self, text):
        params = urllib.parse.urlencode({'voice': 'en-US_MichaelVoice'})
        escaped_text = xml_sax_utils.escape(
            text,
            entities={
                '\"': '&quot;',
                "\'": '&apos;',
                '\&': '&amp;',
                '\<': '&lt;',
                '\>': '&gt;'
            }
        )
        post_data = {
            'text': f'''
            <speak version="1.0">
                <prosody rate="150">{escaped_text}</prosody>
            </speak>
            '''
        }

        http_request = HTTPRequest(
            f'{self.api_base_url}?{params}',
            method='POST',
            auth_username=self.auth_username,
            auth_password=self.auth_password,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'audio/mp3;rate=44100'
            },
            body=json.dumps(post_data)
        )

        audio_file = None
        try:
            response: HTTPResponse = await self.http_client.fetch(http_request)
            audio_file = response.body

        except HTTPError as err:
            response: HTTPResponse = err.response
            logger.exception(f'HTTP Error: {err}, response: {response.body}')

        except Exception as err:
            logger.exception(f'Internal Error: {err}')

        finally:
            return audio_file
