#!/usr/bin/env python3.6

import os.path
import argparse
import asyncio
import logging
import logging.config
import sys
import json
import site
import pandas as pd

from collections import Counter

import nltk

from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

project_dir = os.path.dirname(os.path.abspath(__file__))
site.addsitedir(project_dir)

# Change the scripts working directory to the script's own directory,
# so that relative paths will work.
os.chdir(project_dir)

from src.mediator import (
    EnglishMediator
)
from src.utils import log_config_as_dict


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

    async def stat_english_flashcards(self, user):
        logger.info('Stat english flashcards')
        logger.info(f'User: {user}')

        mediator = EnglishMediator()
        is_login = await mediator.login_user(user)
        if not is_login:
            sys.exit(f'Failed to login user: {user}')

        mediator.set_loop(self.loop)
        lemmatizer = WordNetLemmatizer()

        words_counter = Counter()

        flashcards = await mediator.get_flashcards()
        for flashcard in flashcards:
            # Break text into tokens.
            tokenized_text = word_tokenize(flashcard.answer)
            tokenized_text = [word for word in tokenized_text if word.isalpha()]

            # Part-of-Speech(POS) tagging.
            # Identify the grammatical group of a given word.
            tokenized_text_pos = nltk.pos_tag(tokenized_text)
            for word, treebank_tag in tokenized_text_pos:
                word_lem = lemmatizer.lemmatize(
                    word, pos=self.get_wordnet_pos(treebank_tag)
                )
                words_counter[word_lem.lower()] += 1

        with open('data/core_vocabulary.json') as fh:
            core_vocabulary_json = json.load(fh)
            for word in core_vocabulary_json:
                core_vocabulary_json[word]['count'] = 0

        for word, count in words_counter.items():
            if word in core_vocabulary_json:
                core_vocabulary_json[word]['count'] += count
            else:
                core_vocabulary_json[word] = {
                    "level_3000": None,
                    "level_5000": None,
                    "count": count
                }

        core_vocabulary_df = pd.DataFrame.from_dict(
            core_vocabulary_json, orient='index'
        ).reset_index()
        core_vocabulary_df.rename(columns={'index': 'word'}, inplace=True)
        core_vocabulary_df.to_csv(
            "stat_eng_flashcards.csv", index=False, encoding="utf-8"
        )

    @staticmethod
    def get_wordnet_pos(treebank_tag):
        if treebank_tag.startswith('J'):
            return wordnet.ADJ
        elif treebank_tag.startswith('V'):
            return wordnet.VERB
        elif treebank_tag.startswith('N'):
            return wordnet.NOUN
        elif treebank_tag.startswith('R'):
            return wordnet.ADV
        else:
            return wordnet.NOUN


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
