import os
import socket
import json
import enum
import logging
import urllib.parse
import xml.sax.saxutils as xml_sax_utils

from abc import ABC, abstractmethod

from tornado.httpclient import (
    AsyncHTTPClient, HTTPRequest, HTTPResponse, HTTPError
)

logger = logging.getLogger(__name__)


class TextToSpeechAbstract(ABC):

    def __init__(self):
        self.async_http_client = AsyncHTTPClient()

    @abstractmethod
    async def check_connection(self) -> dict:
        """
        Varifies connection to the api with provided credentials. 
        Returns on successful connection:
            {'is_success': True, 'error': None}
        Otherwise:
            {'is_success': False, 'error': <error>}
        """
        pass

    @abstractmethod
    async def synthesize_audio(self, text):
        pass
        

class IBM_EngTextToSpeech(TextToSpeechAbstract):
    """
    Docs: https://cloud.ibm.com/docs/services/text-to-speech/getting-started.html#gettingStarted
    """

    def __init__(self, api_base_url, auth_username, auth_password):
        super().__init__()
        self.api_base_url = api_base_url
        self.auth_username = auth_username
        self.auth_password = auth_password

    async def check_connection(self) -> dict:
        """
        Varifies connection to the api with provided credentials. 
        Returns on successful connection:
            {'is_success': True, 'error': None}
        Otherwise:
            {'is_success': False, 'error': <error>}
        """
        res = {'is_success': True, 'error': None}
        
        params = urllib.parse.urlencode({'voice': 'en-US_MichaelVoice'})
        post_data = {'text': 'hello world'}
        url = f'{self.api_base_url}?{params}'
        http_request = self.form_http_request(url=url, body=post_data)
        response = await self.fetch_response(http_request)

        if not response['is_success']:
            res['is_success'] = False
            res['error'] = response['error']

        return res

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
        url = f'{self.api_base_url}?{params}'
        http_request = self.form_http_request(url=url, body=post_data)
        response = await self.fetch_response(http_request)

        if response['is_success']:
            return response['response']

    def form_http_request(self, url, method='post', headers=None, body=None):
        _headers={
            'Content-Type': 'application/json',
            'Accept': 'audio/mp3;rate=44100'
        }
        if headers is not None:
            _headers.update(headers)

        http_request = HTTPRequest(
            url,
            method=method.upper(),
            auth_username=self.auth_username,
            auth_password=self.auth_password,
            headers=_headers,
            body=json.dumps(body) if method.lower() == 'post' else None
        )
        return http_request

    async def fetch_response(self, http_request: HTTPRequest):
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
            result['response'] = response.body

        else:
            result['is_success'] = False
            result['error'] = response

        if not result['is_success']:
            logger.error(result)

        return result
