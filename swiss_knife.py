#!/usr/bin/env python3.6

import os.path
import random
import argparse
import asyncio
import logging
import logging.config
import json
import sys
import site
import time

from datetime import datetime
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

    async def create_english_flashcards(self, file_path, user, number):
        logger.info('Create english flashcards')
        logger.info(f'File: {file_path}')
        logger.info(f'User: {user}')

        mediator = await self.setup_mediator(user, 'english')
        data = await self.load_data(file_path)

        num_of_created_flashcards = 0

        for datum_index, datum in enumerate(data, start=1):
            if num_of_created_flashcards == number:
                break

            if datum['is_ready_to_add'] and not datum['created']:
                time.sleep(10)
                try:
                    logger.info(f'Processing {datum_index}/{len(data)}')
                    logger.info(f'{datum}')

                    duplicate = await self.get_duplicate(mediator, datum)
                    if duplicate:
                        logger.error('Duplicate')
                        self.errors.append({
                            'flashcard': datum,
                            'error': f'duplicate, flashcard_id: {duplicate.id}'
                        })
                        continue

                    phonetic_transcription = await mediator.get_pronunciation(
                        datum['answer']
                    )
                        
                    flashcard: Flashcard = Flashcard.create(
                        user_id=mediator.get_user_id(),
                        flashcard_type=mediator.name(),
                        question=datum['question'],
                        answer=datum['answer'],
                        source=datum['source'],
                        phonetic_transcription=phonetic_transcription,
                        explanation=datum['explanation'],
                        examples=datum['examples']
                    )
                    await mediator.save_flashcard(flashcard)
                    #await mediator.attach_audio_answer(flashcard)

                    datum['created'] = True
                    num_of_created_flashcards += 1

                except Exception as err:
                    logger.exception(err)
                    self.errors.append({'flashcard': datum, 'error': str(err)})
                    break

        if self.errors:
            now = datetime.now()
            now = now.strftime('%Y_%m_%d_%H_%M_%S')
            err_file = f'swiss_knife_create_eng_flashcards_errors_{now}.json'
            with open(err_file, 'w') as fh:
                fh.write(json.dumps(self.errors, ensure_ascii=False, indent=4))

        await self.dump_data(file_path, data)

        logger.info(
            f'Total: {len(data)}. '
            f'Number of created flashcards: {num_of_created_flashcards}.'
        )

    async def get_duplicate(self, mediator, datum):
        duplicates = await mediator.search_flashcard(
            datum['answer']
        )
        duplicate = None
        for f in duplicates:
            if f['question'] == datum['question']:
                duplicate = f
                break
        return duplicate

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
                sys.exit(f'Failed to login user: {self.user}')

            mediator.set_loop(self.loop)
            return mediator

    async def load_data(self, file_path, shuffle=True):
        logger.info('Loading data ...')
        # [
        #     {
        #         "created": false,
        #         "answer": "good",
        #         "question": "хороший",
        #         "source": "Core vocabulary.",
        #         "explanation": "of a high standard or quality",
        #         "examples": [
        #            "a good hotel",
        #            "good quality cloth"
        #         ],
        #         "is_ready_to_add": true
        #         "created": false
        #     },
        #     ...
        # ]
        with open(file_path) as fh:
            data = json.loads(fh.read())

        if shuffle:
            random.shuffle(data)
        logger.info(f'Loaded data: {len(data)}')
        return data

    async def dump_data(self, file_path, data):
        logger.info('Dumping data ...')
        with open(file_path, 'w') as fh:
            fh.write(json.dumps(data, ensure_ascii=False, indent=4))
        logger.info(f'Dumped data: {len(data)}')

    async def comb(self, file_path):
        logger.info(f'Operation: comb')
        logger.info(f'File: {file_path}')
        
        data = await self.load_data(file_path)
        data.sort(
            key=lambda d: (
                d.get('is_ready_to_add', False), d.get('created', False)
            )
        )
        count_ready = 0
        created = 0
        for d in data:
            if 'is_ready_to_add' in d:
                count_ready += int(d['is_ready_to_add'])
                created += int(d.get('created', False))
            else:
                d['is_ready_to_add'] = False
        print(
            f'Total: {len(data)}. '
            f'Ready to add: {count_ready}. '
            f'Created: {created}.'
        )
        await self.dump_data(file_path, data)

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


def create_english_flashcards(args):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        SwissKnife(loop=loop).create_english_flashcards(
            file_path=args.file,
            user=args.user,
            number=args.num
        )
    )


def comb(args):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(SwissKnife(loop=loop).comb(args.file))


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

    parser_create_eng_flashcards = subparsers.add_parser(
        'create-english-flashcards'
    )
    parser_create_eng_flashcards.add_argument('--file', required=True)
    parser_create_eng_flashcards.add_argument('--user', required=True)
    parser_create_eng_flashcards.add_argument('--num', type=int, required=True)
    parser_create_eng_flashcards.set_defaults(func=create_english_flashcards)

    parser_comb = subparsers.add_parser('comb')
    parser_comb.add_argument('--file', required=True)
    parser_comb.set_defaults(func=comb)

    parser_stat_eng_flashcards = subparsers.add_parser('stat-english-flashcards')
    parser_stat_eng_flashcards.add_argument('--user', required=True)
    parser_stat_eng_flashcards.set_defaults(func=stat_english_flashcards)

    args = parser.parse_args()
    args.func(args)
