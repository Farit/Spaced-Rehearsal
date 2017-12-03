import json
import re
import asyncio


class WebServer(asyncio.Protocol):

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        self.transport = transport

    def data_received(self, data):
        message = data.decode('utf-8')
        path = self.get_path(message)

        if path == '/':
            http_response = self.index_page_response()
        elif path == '/js/lib/d3.js':
            http_response = self.d3_js_response()
        elif path == '/data.json':
            http_response = self.data_response()
        else:
            raise Exception(f'Unkown path: {path!r}')

        self.transport.write(http_response.encode('utf-8'))
        self.transport.close()

    def get_path(self, message):
        lines = message.split('\r\n')
        get_line = lines[0]
        path = re.match(r'GET\s*(?P<path>.*)\s*HTTP.*', get_line)['path']
        return path.strip()

    def form_http_headers(self, content_length, content_type):
        http_headers = """\
            HTTP/1.1 200 OK
            Content-Lenght: {content_length}
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

    def d3_js_response(self):
        with open('web_server/d3.js') as fh:
            content = fh.read()

        http_headers = self.form_http_headers(
            content_length=len(content),
            content_type='text/html'
        )

        return http_headers + content

    def data_response(self):
        data = [
         {"name":"Andy Hunt",
          "title":"Big Boss",
          "age": 68,
          "bonus": True
         },
         {"name":"Charles Mack",
          "title":"Jr Dev",
          "age":24,
          "bonus": False
         }
        ]
        content = json.dumps(data)
        http_headers = self.form_http_headers(
            content_length=len(content),
            content_type='application/json'
        )
        return http_headers + content

