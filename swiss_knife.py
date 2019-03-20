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


project_dir = os.path.dirname(os.path.abspath(__file__))
site.addsitedir(project_dir)

# Change the scripts working directory to the script's own directory,
# so that relative paths will work.
os.chdir(project_dir)

from src.flashcard import Flashcard
from src.mediator import get_mediator
from src.utils import log_config_as_dict, normalize_value


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

    async def create_words(self, file_path, user, number, mediator_name):
        logger.info('Create new flashcards [words]')
        logger.info(f'File: {file_path}')
        logger.info(f'User: {user}')
        logger.info(f'Mediator: {mediator_name}')

        mediator = await self.setup_mediator(user, mediator_name)

        data = await self.load_data(file_path)
        ready_data = [
            d for d in data
            if d.get('is_ready_to_add') and
               not d.get('created') and
               len(d['answer'].strip().split()) == 1
        ]
        created = 0

        for ind, datum in enumerate(ready_data, start=1):
            if created == number:
                break
            time.sleep(1)

            try:
                logger.info(f'Processing {ind}/{len(ready_data)}')
                logger.info(f'{datum}')

                duplicate = await self.get_duplicate(mediator, datum)
                if duplicate:
                    logger.error('Duplicate')
                    self.errors.append({
                        'flashcard': datum,
                        'error': f'duplicate, flashcard_id: {duplicate.id}'
                    })
                    continue
                
                dictionary_inf = await mediator.dictionary.get_information(
                    word=datum['answer']
                )

                if not dictionary_inf.get('spelling'):
                    logger.error('Spelling is missing')
                    self.errors.append({
                        'flashcard': datum,
                        'error': f'spelling is missing: {dictionary_inf}'
                    })
                    continue

                if not dictionary_inf.get('audio_file'):
                    logger.error('Audio file is missing')
                    self.errors.append({
                        'flashcard': datum,
                        'error': f'audio file is missing: {dictionary_inf}'
                    })
                    continue

                flashcard: Flashcard = Flashcard.create(
                    user_id=mediator.get_user_id(),
                    flashcard_type=mediator.name(),
                    question=datum['question'],
                    answer=datum['answer'],
                    source=datum['source'],
                    phonetic_transcription=dictionary_inf['spelling'],
                    explanation=datum['explanation'],
                    examples=datum['examples']
                )
                await mediator.save_flashcard(flashcard)
                await mediator.attach_audio_answer(
                    flashcard, dictionary_inf['audio_file']
                )

                datum['created'] = True
                created += 1

            except Exception as err:
                logger.exception(err)
                self.errors.append({'flashcard': datum, 'error': str(err)})
                break

        if self.errors:
            now = datetime.now()
            now = now.strftime('%Y_%m_%d_%H_%M_%S')
            with open(f'swiss_knife_create_words_errors_{now}.json', 'w') as fh:
                fh.write(json.dumps(self.errors, ensure_ascii=False, indent=4))

        await self.dump_data(file_path, data)
        logger.info(
            f'Total: {len(data)}. '
            f'Ready: {len(ready_data)}. '
            f'Created: {created}'
        )

    async def create_phrases(self, file_path, user, number, mediator_name):
        logger.info('Create new flashcards [phrases]')
        logger.info(f'File: {file_path}')
        logger.info(f'User: {user}')
        logger.info(f'Mediator: {mediator_name}')

        mediator = await self.setup_mediator(user, mediator_name)

        data = await self.load_data(file_path)
        ready_data = [
            d for d in data
            if d.get('is_ready_to_add') and
               not d.get('created') and 
               len(d['answer'].strip().split()) > 1
        ]
        created = 0

        for ind, datum in enumerate(ready_data, start=1):
            if created == number:
                break
            time.sleep(1)

            try:
                logger.info(f'Processing {ind}/{len(ready_data)}')
                logger.info(f'{datum}')

                duplicate = await self.get_duplicate(mediator, datum)
                if duplicate:
                    logger.error('Duplicate')
                    self.errors.append({
                        'flashcard': datum,
                        'error': f'duplicate, flashcard_id: {duplicate.id}'
                    })
                    continue

                phonetic_transcription = (
                    await mediator.dictionary.get_text_phonetic_spelling(
                        datum['answer']
                    )
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
                await mediator.attach_audio_answer(flashcard)

                datum['created'] = True
                created += 1

            except Exception as err:
                logger.exception(err)
                self.errors.append({'flashcard': datum, 'error': str(err)})
                break

        if self.errors:
            now = datetime.now()
            now = now.strftime('%Y_%m_%d_%H_%M_%S')
            with open(f'swiss_knife_create_phrases_errors_{now}.json', 'w') as fh:
                fh.write(json.dumps(self.errors, ensure_ascii=False, indent=4))

        await self.dump_data(file_path, data)
        logger.info(
            f'Total: {len(data)}. '
            f'Ready: {len(ready_data)}. '
            f'Created: {created}'
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
        mediator = get_mediator(mediator_name)
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


def create_words(args):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        SwissKnife(loop=loop).create_words(
            file_path=args.file,
            user=args.user,
            number=args.num,
            mediator_name='english'
        )
    )


def create_phrases(args):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        SwissKnife(loop=loop).create_phrases(
            file_path=args.file,
            user=args.user,
            number=args.num,
            mediator_name='english'
        )
    )


def comb(args):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(SwissKnife(loop=loop).comb(args.file))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    parser_create_words = subparsers.add_parser('create_words')
    parser_create_words.add_argument('--file', required=True)
    parser_create_words.add_argument('--user', required=True)
    parser_create_words.add_argument('--num', type=int, required=True)
    parser_create_words.set_defaults(func=create_words)

    parser_create_phrases = subparsers.add_parser('create_phrases')
    parser_create_phrases.add_argument('--file', required=True)
    parser_create_phrases.add_argument('--user', required=True)
    parser_create_phrases.add_argument('--num', type=int, required=True)
    parser_create_phrases.set_defaults(func=create_phrases)

    parser_comb = subparsers.add_parser('comb')
    parser_comb.add_argument('--file', required=True)
    parser_comb.set_defaults(func=comb)

    args = parser.parse_args()
    args.func(args)
