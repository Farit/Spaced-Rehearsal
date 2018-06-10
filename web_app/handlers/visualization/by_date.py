# -*- coding: utf-8 -*-

import json
import logging

from web_app.handlers import base

logger = logging.getLogger(__name__)


class VisualizationByDateHandler(base.BaseRequestHandler):

    def get(self):
        data = self.db_session.get_vis_by_date(user_id=self.current_user['id'])
        self.write(json.dumps(data))
