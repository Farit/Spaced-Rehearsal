# -*- coding: utf-8 -*-

import logging
import tornado.gen
import tornado.web

logger = logging.getLogger(__name__)


class BaseRequestHandler(tornado.web.RequestHandler):

    @tornado.gen.coroutine
    def prepare(self):
        if not self.settings.get('user_id'):
            raise tornado.web.HTTPError(status_code=403)
        self.db_session = self.settings['db_session']

    def get_current_user(self):
        """Determines current user from session"""
        return {'id': self.settings['user_id']}



