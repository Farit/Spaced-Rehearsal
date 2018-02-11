import json
import string

from src.config import ConfigAdapter
from src.db_session import DBSession


class Route:
    def __init__(self):
        self.views = []

    def __call__(self, request_method, path):
        def decorator(method):
            self.views.append((request_method, path, method.__name__))
            return method
        return decorator


route = Route()


class Response:

    def __init__(self, status, headers=None, data=None):
        self.status = status
        self.headers = headers or []
        self.data = data or ''


class WebApp:

    def __init__(self, user_id):
        self.config = ConfigAdapter(filename='config.cfg')
        self.db_session = DBSession(self.config['database'].get('name'))
        self.user_id = user_id

    def __call__(self, environ, start_response):
        response = None
        for request_method, path, method_name in route.views:
            is_request_method_equal = (
                request_method.lower() == environ['REQUEST_METHOD'].lower()
            )
            is_path_equal = path.lower() == environ['PATH_INFO']

            if is_request_method_equal and is_path_equal:
                response: Response = getattr(self, method_name)()
                break

        if response is None:
            response: Response = Response('404')

        start_response(response.status, response.headers)
        return response.data

    @route('GET', '/')
    def index(self):
        with open('web_server/index.html') as fh:
            content_template = string.Template(fh.read())

        num_of_flashcards = self.db_session.count_flashcards(
            user_id=self.user_id
        )
        content = content_template.substitute(
            num_of_flashcards=num_of_flashcards
        )
        response = Response(
            status='200 OK',
            headers=[
                ('Content-Type', 'text/html')
            ],
            data=content
        )
        return response

    @route('GET', '/d3.js')
    def d3_js(self):
        with open(f'web_server/d3.js') as fh:
            content = fh.read()

        response = Response(
            status='200 OK',
            headers=[
                ('Content-Type', 'text/plain')
            ],
            data=content
        )
        return response

    @route('GET', '/d3-scale.js')
    def d3_scale_js(self):
        with open(f'web_server/d3-scale.js') as fh:
            content = fh.read()

        response = Response(
            status='200 OK',
            headers=[
                ('Content-Type', 'text/plain')
            ],
            data=content
        )
        return response

    @route('GET', '/d3-scale-chromatic.js')
    def d3_scale_chromatic_js(self):
        with open(f'web_server/d3-scale-chromatic.js') as fh:
            content = fh.read()

        response = Response(
            status='200 OK',
            headers=[
                ('Content-Type', 'text/plain')
            ],
            data=content
        )
        return response

    @route('GET', '/vis_by_date.json')
    def vis_by_date(self):
        data = self.db_session.get_vis_by_date(user_id=self.user_id)
        content = json.dumps(data)

        response = Response(
            status='200 OK',
            headers=[
                ('Content-Type', 'application/json')
            ],
            data=content
        )
        return response

