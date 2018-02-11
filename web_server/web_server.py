import asyncio

from src.config import ConfigAdapter
from src.db_session import DBSession
from .web_app import WebApp


class WebServer(asyncio.Protocol):

    def __init__(self):
        self.config = ConfigAdapter(filename='config.cfg')
        self.db_session = DBSession(self.config['database'].get('name'))
        self.headers_set = None
        self.request_method = None
        self.request_version = None
        self.path = None

    @classmethod
    def set_app(cls, user_id):
        cls.application = WebApp(user_id=user_id)

    def get_environ(self):
        env = dict()
        env['REQUEST_METHOD'] = self.request_method  # GET
        env['PATH_INFO'] = self.path  # /hello
        return env

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        self.transport = transport

    def data_received(self, data):
        try:
            self.prepare()
            data = data.decode('utf-8')
            response = self.handle_one_request(data)
            self.transport.write(response.encode('utf-8'))
        finally:
            self.transport.close()

    def prepare(self):
        self.headers_set = []
        self.request_method = None
        self.request_version = None
        self.path = None

    def handle_one_request(self, request_data):
        self.parse_request(request_data)
        env = self.get_environ()
        result = self.application(env, self.start_response)
        return self.finish_response(result)

    def parse_request(self, text):
        request_line = text.splitlines()[0]
        request_line = request_line.rstrip('\r\n')
        (
            self.request_method,  # GET
            self.path,            # /hello
            self.request_version  # HTTP/1.1
        ) = request_line.split()

    def start_response(self, status, response_headers):
        server_headers = [
            ('Date', 'Sun, 11 Feb 2018 12:05:48 GMT'),
            ('Server', 'SpacedRehearsalServer 0.1')
        ]
        self.headers_set = [status, response_headers + server_headers]

    def finish_response(self, result):
        status, response_headers = self.headers_set
        response = f'HTTP/1.1 {status}\r\n'
        for header_key, header_value in response_headers:
            response += f'{header_key}: {header_value}\r\n'
        response += '\r\n'
        for data in result:
            response += data
        return response
