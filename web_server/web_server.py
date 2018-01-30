import json
import re
import asyncio

from src.config import ConfigAdapter
from src.db_session import DBSession


class WebServer(asyncio.Protocol):
    USER_ID = None

    def __init__(self):
        self.config = ConfigAdapter(filename='config.cfg')
        self.db_session = DBSession(self.config['database'].get('name'))

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        self.transport = transport

    def data_received(self, data):
        message = data.decode('utf-8')
        path = self.get_path(message)

        if path == '/':
            http_response = self.index_page_response()
        elif path == '/d3.js':
            http_response = self.d3_js_response(d3_file='d3.js')
        elif path == '/d3-scale.js':
            http_response = self.d3_js_response(d3_file='d3-scale.js')
        elif path == '/d3-scale-chromatic.js':
            http_response = self.d3_js_response(d3_file='d3-scale-chromatic.js')
        elif path == '/vis_by_date.json':
            http_response = self.vis_by_date_response()
        else:
            http_response = self.not_found_response()

        self.transport.write(http_response.encode('utf-8'))
        self.transport.close()

    @staticmethod
    def get_path(message):
        lines = message.split('\r\n')
        get_line = lines[0]
        path = re.match(r'GET\s*(?P<path>.*)\s*HTTP.*', get_line)['path']
        return path.strip()

    @staticmethod
    def form_http_headers(content_length, content_type):
        http_headers = """\
            HTTP/1.1 200 OK
            Content-Length: {content_length}
            Content-type: {content_type}
            Connection: Closed

        """.format(content_type=content_type, content_length=content_length)
        return http_headers

    def index_page_response(self):
        with open('web_server/index.html') as fh:
            content = fh.read()

        http_headers = self.form_http_headers(
            content_length=len(content),
            content_type='text/html'
        )

        return http_headers + content

    def d3_js_response(self, d3_file):
        with open(f'web_server/{d3_file}') as fh:
            content = fh.read()

        http_headers = self.form_http_headers(
            content_length=len(content),
            content_type='text/html'
        )

        return http_headers + content

    def vis_by_date_response(self):
        data = self.db_session.get_vis_by_date(user_id=self.USER_ID)
        content = json.dumps(data)
        http_headers = self.form_http_headers(
            content_length=len(content),
            content_type='application/json'
        )
        return http_headers + content

    @staticmethod
    def not_found_response():
        http_headers = """\
            HTTP/1.1 404
            Connection: Closed

        """
        return http_headers


