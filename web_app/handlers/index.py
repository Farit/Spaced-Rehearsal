# -*- coding: utf-8 -*-

import logging

from web_app.handlers import base

logger = logging.getLogger(__name__)


class IndexHandler(base.BaseRequestHandler):

    def get(self):
        total = self.db_session.count_flashcards(
            user_id=self.current_user['id']
        )
        num_of_flashcards = total['text'] + total['audio']
        self.render('index.html', num_of_flashcards=num_of_flashcards)
