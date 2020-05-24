#!/usr/bin/env python3.6

import os
import shutil
import pathlib
import json
import sys
import asyncio
import os.path
import argparse
import logging
import logging.config
import textwrap
import site

from datetime import datetime

project_dir = os.path.dirname(os.path.abspath(__file__))
site.addsitedir(project_dir)

# Change the scripts working directory to the script's own directory,
# so that relative paths will work.
os.chdir(project_dir)

from src.app import SpacedRehearsal
from src.flashcard import Flashcard
from src.mediator import (
    GeneralMediator,
    EnglishMediator,
    EnglishRussianMediator
)
from src.dictionary import (
    OxfordEngDict
)
from src.utils import log_config_as_dict
from src.config import ConfigAdapter
from src.formatting import Formatting


logging.config.dictConfig(log_config_as_dict)
logger_tu = logging.getLogger('terminal_utility')


def get_dictionary(args: argparse.Namespace):
    config = ConfigAdapter(filename='config.cfg')
    dictionary = None
    if args.dictionary == 'oxford':
        app_id = os.getenv('OXFORD_DICTIONARY_APP_ID')
        app_key = os.getenv('OXFORD_DICTIONARY_APP_KEY')
        api_base_url = config['dictionary']['oxford_dict_api_base_url']
        dictionary = OxfordEngDict(
            api_base_url=api_base_url,
            app_id=app_id,
            app_key=app_key,
            dictionary_db_path=config['dictionary']['dict_database']
        )

        loop = asyncio.new_event_loop()
        res = loop.run_until_complete(dictionary.check_connection())
        loop.close()
        if not res['is_success']:
            formatting = Formatting()
            msg = formatting.red(
                'Oxford dictionary API connection check failed.\n'
                'Please verify your internet connection or api credentials.'
            )
            print(msg)
            dictionary = None
    return dictionary


def general_mediator(args: argparse.Namespace):
    mediator = GeneralMediator()
    spaced_rehearsal = SpacedRehearsal(mediator=mediator)
    spaced_rehearsal.run()


def english_mediator(args: argparse.Namespace):
    mediator = EnglishMediator(dictionary=get_dictionary(args))
    spaced_rehearsal = SpacedRehearsal(mediator=mediator)
    spaced_rehearsal.run()


def eng_rus_mediator(args: argparse.Namespace):
    mediator = EnglishRussianMediator(dictionary=get_dictionary(args))
    spaced_rehearsal = SpacedRehearsal(mediator=mediator)
    spaced_rehearsal.run()


def dump_eng_flashcards(args: argparse.Namespace):
    async def _wrapper(loop, user, field, value):
        logger_tu.info('Dump english flashcards')
        logger_tu.info('Field: %s', field)
        logger_tu.info('Value: %s', value)
        logger_tu.info(f'User: {user}')

        mediator = EnglishMediator()
        is_login = await mediator.login_user(user)
        if not is_login:
            sys.exit(f'Failed to login user: {user}')

        mediator.set_loop(loop)

        number_of_flashcards = 0
        dump = []

        flashcards = await mediator.get_flashcards()
        for flashcard in flashcards:
            if getattr(flashcard, field) == value:
                flashcard_dump = {}
                for f, v in flashcard:
                    if f == 'examples':
                        flashcard_dump[f] = json.dumps(v)
                    else:
                        flashcard_dump[f] = str(v)
                dump.append(flashcard_dump)
                number_of_flashcards += 1

        logger_tu.info(f'Number of flashcards: {number_of_flashcards}')
        now = datetime.now()
        now = now.strftime('%Y_%m_%d_%H_%M_%S')
        file_path = f'dump_eng_flashcards_{now}.json'
        logger_tu.info('Dumping data into %s', file_path)
        with open(file_path, 'w') as fh:
            fh.write(json.dumps(dump, ensure_ascii=False, indent=4))

    _loop = asyncio.get_event_loop()
    _loop.run_until_complete(_wrapper(
        loop=_loop,
        user=args.user,
        field=args.field,
        value=args.value
    ))


def create_eng_flashcards(args: argparse.Namespace):
    async def _wrapper(loop, user, file_path):
        logger_tu.info('Create english flashcards')
        logger_tu.info('User: %s', user)
        logger_tu.info('File: %s', file_path)

        mediator = EnglishMediator()
        is_login = await mediator.login_user(user)
        if not is_login:
            sys.exit(f'Failed to login user: {user}')

        mediator.set_loop(loop)

        with open(file_path) as fh:
            data = json.loads(fh.read())
        logger_tu.info(f'Loaded data: {len(data)}')

        for datum in data:
            logger_tu.info('Processing answer: %s', datum['answer'])
            flashcard: Flashcard = Flashcard.create(
                user_id=mediator.get_user_id(),
                flashcard_type=mediator.name(),
                question=datum['question'],
                answer=datum['answer'],
                source=datum['source'],
                phonetic_transcription=datum['phonetic_transcription'],
                explanation=datum['explanation'],
                examples=json.loads(datum['examples'])
            )
            await mediator.save_flashcard(flashcard)

    _loop = asyncio.get_event_loop()
    _loop.run_until_complete(_wrapper(
        loop=_loop,
        user=args.user,
        file_path=args.file,
    ))


def create_audio_eng_flashcards(args: argparse.Namespace):
    async def _wrapper(loop, user, dir_path, source):
        logger_tu.info('Create audio english flashcards')
        logger_tu.info('User: %s', user)
        logger_tu.info('Directory: %s', dir_path)
        logger_tu.info('Source: %s', source)

        mediator = EnglishMediator()
        is_login = await mediator.login_user(user)
        if not is_login:
            sys.exit(f'Failed to login user: {user}')

        mediator.set_loop(loop)

        data = []
        for dirpath, dirnames, filenames in os.walk(dir_path):
            for file_name in filenames:
                file_path = pathlib.Path(os.path.join(dirpath, file_name))
                if file_path.suffix in ['.mp3']:
                    data.append({
                        'audio_file_path': file_path,
                        'text_file_path': file_path.with_suffix('.txt'),
                    })

        for datum in data:
            now = datetime.now()
            now = now.strftime('%Y_%m_%d_%H_%M_%S_%f')

            audio_suffix = datum['audio_file_path'].suffix
            file_name = f'__audio__{now}{audio_suffix}'
            flashcard_audio_file_path = pathlib.Path(
                os.path.join(mediator.get_audio_dir(), file_name)
            )
            flashcard_audio_file_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(datum['audio_file_path'], flashcard_audio_file_path)

            question = file_name
            with open(datum['text_file_path']) as fh:
                answer = fh.read().strip().capitalize()

            logger_tu.info('Processing %s answer: %s', question, answer)
            flashcard: Flashcard = Flashcard.create(
                user_id=mediator.get_user_id(),
                flashcard_type=mediator.name(),
                question=question,
                answer=answer,
                source=source
            )
            await mediator.save_flashcard(flashcard)

    _loop = asyncio.get_event_loop()
    _loop.run_until_complete(_wrapper(
        loop=_loop,
        user=args.user,
        dir_path=args.dir_path,
        source=args.source
    ))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.set_defaults(func=general_mediator)

    subparsers = parser.add_subparsers()

    english_mediator_parser = subparsers.add_parser('english-mediator')
    english_mediator_parser.add_argument('--dictionary', choices=['oxford'])
    english_mediator_parser.set_defaults(func=english_mediator)

    eng_rus_mediator_parser = subparsers.add_parser('eng-rus-mediator')
    eng_rus_mediator_parser.add_argument('--dictionary', choices=['oxford'])
    eng_rus_mediator_parser.set_defaults(func=eng_rus_mediator)

    dump_eng_flashcards_parser = subparsers.add_parser(
        'dump-english-flashcards',
        help=textwrap.dedent('''
        Dump English flashcards by specifying field name and its value.
        pipenv run python run.py dump-english-flashcards --user farit
        --field source --value "English phrases v0.5."
        ''')
    )
    dump_eng_flashcards_parser.add_argument(
        '--user', required=True,
        help='Enter user name.'
    )
    dump_eng_flashcards_parser.add_argument(
        '--field', required=True, choices=['source'],
        help='Dumps flashcards by considering this field.'
    )
    dump_eng_flashcards_parser.add_argument(
        '--value', required=True,
        help='Field should have this value to be dumped.'
    )
    dump_eng_flashcards_parser.set_defaults(func=dump_eng_flashcards)

    create_eng_flashcards_parser = subparsers.add_parser(
        'create-english-flashcards',
        help=textwrap.dedent('''
        Creates english flashcards by loading the file:
        [
            {
                "question": "Я поймал его на прослушивании нашего разговора. (Use past simple)",
                "answer": "I caught him eavesdropping on our conversation.",
                "source": "English phrases v0.5.",
                "phonetic_transcription": "I caught",
                "explanation": "[eavesdrop] to deliberately listen secretly to other people’s conversations.",
                "examples": "[\"Sue was able to eavesdrop on them through the open window.\"]"
            }
        ]
        ''')
    )
    create_eng_flashcards_parser.add_argument('--file', required=True)
    create_eng_flashcards_parser.add_argument('--user', required=True)
    create_eng_flashcards_parser.set_defaults(func=create_eng_flashcards)

    create_audio_eng_flashcards_parser = subparsers.add_parser(
        'create-audio-eng-flashcards',
        help=textwrap.dedent('''
        Directory structure example:
            rudy_film/
            ├── 340.mp3
            ├── 340.txt
            ├── 352.mp3
            └── 352.txt
        ''')
    )
    create_audio_eng_flashcards_parser.add_argument('--dir-path', required=True)
    create_audio_eng_flashcards_parser.add_argument('--user', required=True)
    create_audio_eng_flashcards_parser.add_argument('--source', required=True)
    create_audio_eng_flashcards_parser.set_defaults(func=create_audio_eng_flashcards)

    args = parser.parse_args()
    args.func(args)
