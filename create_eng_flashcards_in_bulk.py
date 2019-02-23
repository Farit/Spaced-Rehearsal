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
from src.utils import log_config_as_dict


log_config_as_dict['root'] = {
    'handlers': ['console_stdout_simple', 'console_stderr_simple', 'file'],
    'level': 'DEBUG'
}
logging.config.dictConfig(log_config_as_dict)
logger = logging.getLogger(__name__)


class CreateInBulk:

    def __init__(self, loop, file_path, user, count, mediator_name):
        self.loop = loop
        self.file_path = file_path
        self.user = user
        self.count = count
        self.mediator_name = mediator_name
        self.errors = []

    async def run(self):
        logger.info(f'File: {self.file_path}')
        logger.info(f'User: {self.user}')
        logger.info(f'Mediator: {self.mediator_name}')

        mediator = get_mediator(self.mediator_name)
        is_login = await mediator.login_user(self.user)
        if not is_login:
            sys.exit(f'Failed to login user: {self.user}')

        mediator.set_loop(self.loop)

        data = await self.load_data()
        total = 0
        added = 0

        for ind, datum in enumerate(data, start=1):
            if added == self.count:
                break

            time.sleep(1)
            total += 1

            try:
                logger.info(f'Processing {ind}/{len(data)}')
                logger.info(f'{datum}')

                if len(datum['answer'].split()) != 1:
                    logger.error('Compound answer.')
                    self.errors.append({
                        'flashcard': datum,
                        'error': f'compound answer'
                    })
                    continue

                duplicates = await mediator.search_flashcard(
                    datum['answer']
                )
                duplicate = None
                for f in duplicates:
                    if f['question'] == datum['question']:
                        duplicate = f
                        break

                if duplicate is not None:
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
                added += 1

            except Exception as err:
                logger.exception(err)
                self.errors.append({'flashcard': datum, 'error': str(err)})

        if self.errors:
            now = datetime.now()
            now = now.strftime('%Y_%m_%d_%H_%M_%S')
            with open(f'create_eng_in_bulk_errors_{now}.json', 'w') as fh:
                json.dump(self.errors, fh)

        logger.info(f'Total: {total}. Added: {added}')
            

    async def load_data(self):
        logger.info('Loading data ...')
        # [
        #     {
        #         "answer": "good",
        #         "question": "хороший",
        #         "source": "Core vocabulary.",
        #         "explanation": "of a high standard or quality",
        #         "examples": [
        #            "a good hotel",
        #            "good quality cloth"
        #         ]
        #     },
        #     ...
        # ]
        with open(self.file_path) as fh:
            data = json.loads(fh.read())

        random.shuffle(data)
        logger.info(f'Loaded data: {len(data)}')
        return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', required=True)
    parser.add_argument('--user', required=True)
    parser.add_argument('--count', type=int, required=True)
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        CreateInBulk(
            loop=loop,
            file_path=args.file,
            user=args.user,
            count=args.count,
            mediator_name='english'
        ).run()
    )
