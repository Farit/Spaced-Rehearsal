#!/usr/bin/env python3.6

import os
import sys
import asyncio
import os.path
import argparse
import logging.config
import site

project_dir = os.path.dirname(os.path.abspath(__file__))
site.addsitedir(project_dir)

# Change the scripts working directory to the script's own directory,
# so that relative paths will work.
os.chdir(project_dir)

from src.app import SpacedRehearsal
from src.mediator import (
    EnglishMediator
)
from src.dictionary import (
    OxfordEngDict
)
from src.utils import log_config_as_dict
from src.config import ConfigAdapter


logging.config.dictConfig(log_config_as_dict)


def english_mediator(args):
    config = ConfigAdapter(filename='config.cfg')

    dictionary = None
    if args.dictionary == 'oxford':
        app_id = os.getenv('OXFORD_DICTIONARY_APP_ID')
        app_key = os.getenv('OXFORD_DICTIONARY_APP_KEY')
        api_base_url = config['dictionary']['oxford_dict_api_base_url']
        dictionary = OxfordEngDict(api_base_url, app_id, app_key)

        loop = asyncio.new_event_loop()
        res = loop.run_until_complete(dictionary.check_connection())
        loop.close()
        if not res['is_success']:
            sys.exit(
                'Oxford dictionary API connection check failed.\n'
                'Please verify your internet connection or api credentials.'
            )

    mediator = EnglishMediator(dictionary=dictionary)
    spaced_rehearsal = SpacedRehearsal(mediator=mediator)
    spaced_rehearsal.run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    english_mediator_parser = subparsers.add_parser('english-mediator')
    english_mediator_parser.add_argument('--dictionary', choices=['oxford'])
    english_mediator_parser.set_defaults(func=english_mediator)

    args = parser.parse_args()
    args.func(args)
