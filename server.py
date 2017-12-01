import asyncio


class WebServer(asyncio.Protocol):
    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(peername))
        self.transport = transport

    def data_received(self, data):
        message = data.decode()
        print('Data received: {!r}'.format(message))

        http_response = self.form_http_response()
        print('Send: {!r}'.format(http_response))
        self.transport.write(http_response.encode('utf-8'))

        print('Close the client socket')
        self.transport.close()

    def form_http_response(self):
        http_response = """\
            HTTP/1.1 200 OK

            Hello, World!
            """
        return http_response
