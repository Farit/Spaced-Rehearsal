# -*- coding: utf-8 -*-

import logging

from web_app.handlers import base

logger = logging.getLogger(__name__)


class DefaultHandler(base.BaseRequestHandler):

    def get(self):
        logger.warning('Page %s not found', self.request.full_url())
        self.set_status(status_code=404)
        self.render('default.html')
