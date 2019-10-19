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
    GeneralMediator,
    EnglishMediator,
    EnglishRussianMediator
)
from src.dictionary import (
    OxfordEngDict
)
from src.text_to_speech import (
    IBM_EngTextToSpeech
)
from src.utils import log_config_as_dict
from src.config import ConfigAdapter


logging.config.dictConfig(log_config_as_dict)


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
            print(
                'Oxford dictionary API connection check failed.\n'
                'Please verify your internet connection or api credentials.'
            )
            dictionary = None
    return dictionary


def get_text_to_speech(args: argparse.Namespace):
    config = ConfigAdapter(filename='config.cfg')
    text_to_speech = None
    if args.text_to_speech == 'ibm':
        auth_username = os.getenv('IBM_TEXT_TO_SPEECH_AUTH_USERNAME')
        auth_password = os.getenv('IBM_TEXT_TO_SPEECH_AUTH_PASSWORD')
        api_base_url = config['text_to_speech']['ibm_api_url']
        text_to_speech = IBM_EngTextToSpeech(
            api_base_url=api_base_url,
            auth_username=auth_username,
            auth_password=auth_password
        )

        loop = asyncio.new_event_loop()
        res = loop.run_until_complete(text_to_speech.check_connection())
        loop.close()
        if not res['is_success']:
            print(
                'IBM text to speech API connection check failed.\n'
                'Please verify your internet connection or api credentials.'
            )
            text_to_speech = None
    return text_to_speech


def general_mediator(args: argparse.Namespace):
    mediator = GeneralMediator()
    spaced_rehearsal = SpacedRehearsal(mediator=mediator)
    spaced_rehearsal.run()


def english_mediator(args: argparse.Namespace):
    mediator = EnglishMediator(
        dictionary=get_dictionary(args),
        text_to_speech=get_text_to_speech(args)
    )
    spaced_rehearsal = SpacedRehearsal(mediator=mediator)
    spaced_rehearsal.run()


def eng_rus_mediator(args: argparse.Namespace):
    mediator = EnglishRussianMediator(
        dictionary=get_dictionary(args),
        text_to_speech=get_text_to_speech(args)
    )
    spaced_rehearsal = SpacedRehearsal(mediator=mediator)
    spaced_rehearsal.run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.set_defaults(func=general_mediator)

    subparsers = parser.add_subparsers()

    english_mediator_parser = subparsers.add_parser('english-mediator')
    english_mediator_parser.add_argument('--dictionary', choices=['oxford'])
    english_mediator_parser.add_argument('--text-to-speech', choices=['ibm'])
    english_mediator_parser.set_defaults(func=english_mediator)

    eng_rus_mediator_parser = subparsers.add_parser('eng-rus-mediator')
    eng_rus_mediator_parser.add_argument('--dictionary', choices=['oxford'])
    eng_rus_mediator_parser.add_argument('--text-to-speech', choices=['ibm'])
    eng_rus_mediator_parser.set_defaults(func=eng_rus_mediator)

    args = parser.parse_args()
    args.func(args)
