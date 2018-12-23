# -*- coding: utf-8 -*-

import os.path

import tornado.web
import tornado.ioloop
import tornado.httpserver


from src.config import ConfigAdapter
from src.db_session import DBSession
from web_app.urls import urls
from web_app.handlers import default


class Application:

    def __init__(self, flashcard_type):
        self.config = ConfigAdapter(filename='config.cfg')
        self.db_session = DBSession(
            self.config['database'].get('name'),
            flashcard_type=flashcard_type
        )

        self.address = self.config['server'].get('host')
        self.port = self.config['server'].getint('port')
        self.user_id = None

        app_root = os.path.dirname(os.path.abspath(__file__))
        self.app = tornado.web.Application(
            handlers=urls,
            template_path=os.path.join(app_root, 'templates'),
            static_path=os.path.join(app_root, 'static'),
            default_handler_class=default.DefaultHandler,
            db_session=self.db_session
        )
        self.http_server = tornado.httpserver.HTTPServer(self.app)

    def set_user_id(self, user_id):
        self.user_id = user_id
        self.app.settings['user_id'] = user_id

    def start(self):
        self.http_server.listen(address=self.address, port=self.port)




