#!/usr/bin/env python3.6

import os.path
import argparse
import asyncio
import logging
import logging.config
import sys
import site

from collections import Counter


project_dir = os.path.dirname(os.path.abspath(__file__))
site.addsitedir(project_dir)

# Change the scripts working directory to the script's own directory,
# so that relative paths will work.
os.chdir(project_dir)

from src.flashcard import Flashcard
from src.mediator import (
    EnglishMediator
)
from src.dictionary import (
    OxfordEngDict
)
from src.utils import (
    log_config_as_dict,
    normalize_eng_word
)
from src.config import ConfigAdapter


log_config_as_dict['root'] = {
    'handlers': ['console_stdout_simple', 'console_stderr_simple', 'file'],
    'level': 'DEBUG'
}
logging.config.dictConfig(log_config_as_dict)
logger = logging.getLogger(__name__)


class SwissKnife:

    def __init__(self, loop):
        self.loop = loop
        self.errors = []

    async def setup_mediator(self, user, mediator_name):
        config = ConfigAdapter(filename='config.cfg')

        if mediator_name == 'english':
            app_id = os.getenv('OXFORD_DICTIONARY_APP_ID')
            app_key = os.getenv('OXFORD_DICTIONARY_APP_KEY')
            api_base_url = config['dictionary']['oxford_dict_api_base_url']
            dictionary = OxfordEngDict(
                api_base_url, app_id, app_key,
                dictionary_db_path=config['dictionary']['dict_database']
            )

            res = await dictionary.check_connection()
            if not res['is_success']:
                sys.exit(
                    'Oxford dictionary API connection check failed.\n'
                    'Please verify your internet connection or api credentials.'
                )

            mediator = EnglishMediator(dictionary=dictionary)
            is_login = await mediator.login_user(user)
            if not is_login:
                sys.exit(f'Failed to login user: {user}')

            mediator.set_loop(self.loop)
            return mediator

    async def stat_english_flashcards(self, user):
        logger.info('Stat english flashcards')
        logger.info(f'User: {user}')

        mediator = await self.setup_mediator(user, 'english')

        number_of_flashcards = 0
        words_counter = Counter()

        flashcards = await mediator.get_flashcards()
        for flashcard in flashcards:
            number_of_flashcards += 1
            for word in flashcard.answer.split():
                words_counter[normalize_eng_word(word)] += 1

        logger.info(f'Number of flashcards: {number_of_flashcards}')
        logger.info(f'Number of words: {sum(words_counter.values())}')
        logger.info(f'Number of unique words: {len(words_counter)}')


def stat_english_flashcards(args):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        SwissKnife(loop=loop).stat_english_flashcards(
            user=args.user
        )
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    parser_stat_eng_flashcards = subparsers.add_parser('stat-english-flashcards')
    parser_stat_eng_flashcards.add_argument('--user', required=True)
    parser_stat_eng_flashcards.set_defaults(func=stat_english_flashcards)

    args = parser.parse_args()
    args.func(args)
