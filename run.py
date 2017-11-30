#!/usr/bin/env python3.6

import re
import random
import string
import signal
import asyncio
import functools

from datetime import datetime, timedelta

from config import ConfigAdapter
from db_session import DBSession
from utils import TermColor, Communication, handle_eof, datetime_now


class BaseClass:

    def __init__(self):
        self.config = ConfigAdapter(filename='config.cfg')

    @staticmethod
    def normalize_sentence(sentence):
        _normalized = ''
        for word in sentence.split(' '):
            word = word.strip()
            if word:
                word = word.lower()
                prefix = f' ' if word not in string.punctuation else f''
                _normalized += prefix + word
        return _normalized.strip().rstrip('.').rstrip(' ')

    @staticmethod
    def remove_whitespaces(sentence):
        return re.sub(r'[\s]{2,}', r' ', sentence).strip()

    @staticmethod
    def request_input(request_msgs, request_answers):
        assert isinstance(request_answers, tuple), \
            f'request answers must be tuple'
        assert isinstance(request_msgs, list), f'request msg must be list'

        action = None
        while action not in request_answers:
            for msg in request_msgs:
                Communication.print_output(*msg)
            if action is not None:
                Communication.print_output(
                    TermColor.red(f'Invalid command: {action}')
                )
            action = Communication.print_action()
            action = action.strip()
        return action


class SpacedRehearsal(BaseClass):

    def __init__(self):
        super().__init__()
        self.loop = asyncio.get_event_loop()
        self.db_session = DBSession(
            self.config['database'].get('name'), setup_db=True
        )
        self.user = None
        self.set_signal_handler('sigint')
        self.set_signal_handler('sigterm')

    def run(self):
        try:
            self.loop.call_soon(self.login)
            self.loop.run_forever()
        finally:
            self.loop.close()

    def set_signal_handler(self, signame):
        self.loop.add_signal_handler(
            getattr(signal, signame.upper()),
            functools.partial(self.exit, signame)
        )

    def exit(self, signame):
        Communication.print_output(
            f'Got signal {TermColor.bold(f"{signame}")}',
            f'{TermColor.red("Exit")}'
        )
        if self.user:
            Communication.print_output(f'Bye {self.user["login"]}!')
        self.db_session.close()
        self.loop.stop()

    @handle_eof('quit')
    def login(self):
        login_name = Communication.print_input('Login')
        user = self.db_session.get_user(login_name)
        if user is None:
            action = self.request_input(
                request_answers=('y', 'n', 'q'),
                request_msgs=[
                    (
                        TermColor.red(f'User "{login_name}" does not exist.'),
                        'Do you want to create [y/n] ?',
                        f'If you want to {TermColor.red("quit")} '
                        f'please type [{TermColor.red("q")}].'
                    )
                ]
            )
            action = {'y': 'register', 'n': 'login', 'q': 'quit'}[action]
            if action == 'register':
                self.register(login_name=login_name)
            else:
                getattr(self, action)()

        else:
            self.user = self.db_session.get_user(login_name)
            self.loop.call_soon(self.choose_action)

    def register(self, login_name):
        self.db_session.register_user(login_name)
        Communication.print_output(f'User {login_name} is registered!')
        self.loop.call_soon(self.login)

    @handle_eof('choose_action')
    def choose_action(self):
        total_number = self.db_session.count_flashcards(
            user_id=self.user["id"]
        )
        ready_number = self.db_session.count_flashcards(
            user_id=self.user["id"],
            due=datetime_now()
        )
        action = self.request_input(
            request_answers=('a', 'p', 'q'),
            request_msgs=[
                (
                    f'Do you want to {TermColor.yellow("add")} '
                    f'[{TermColor.yellow("a")}] or to {TermColor.green("play")}'
                    f'[{TermColor.green("p")}] ?',
                    f'Number of the flashcards: {total_number}',
                    f'Number of the flashcards ready to play: {ready_number}',
                    f'If you want to {TermColor.red("quit")}, please type '
                    f'[{TermColor.red("q")}].'
                )
            ]
        )
        action = {'a': 'add', 'p': 'play', 'q': 'quit'}[action]
        getattr(self, action)()

    @handle_eof('choose_action', with_start_new_line=False)
    def play(self):
        _play = None
        try:
            _play = Play(user_id=self.user['id'])
            _play()
            self.loop.call_soon(self.choose_action)
        except EOFError as err:
            if _play:
                _play.print_end(with_start_new_line=True)
            raise err

    @handle_eof('choose_action')
    def add(self):
        AddFlashcard(self.user['id'])()
        self.loop.call_soon(self.choose_action)

    def quit(self):
        self.exit('sigterm')


class Play(BaseClass):

    def __init__(self, user_id):
        super().__init__()
        self.total = 0
        self.count = 0
        self.played = 0
        self.right = 0
        self.wrong = 0
        self.timeout = 0
        self.user_id = user_id
        self.db_session = DBSession(self.config['database'].get('name'))

    def __call__(self):
        flashcards = self.db_session.get_ready_flashcards(user_id=self.user_id)
        random.shuffle(flashcards)
        self.total = len(flashcards)

        for flashcard in flashcards:
            self.count += 1
            side_b, flashcard_side_b, is_timeout = self.play(flashcard)
            result = self.handle_answer(
                flashcard, side_b, flashcard_side_b, is_timeout
            )
            self.print_result(flashcard, result)
            self.played += 1

            if self.played < self.total:
                action = self.request_input(
                    request_answers=('y', 'n'),
                    request_msgs=[
                        (
                            f'Do you want to continue '
                            f'[{TermColor.green("y")}/{TermColor.red("n")}] ?',
                        )
                    ]
                )
                if action == 'n':
                    break

        self.print_end()

    def play(self, flashcard):
        Communication.print_output(
            TermColor.bold(
                f'Flashcard[{flashcard["id"]}] #{self.count} / #{self.total}')
        )
        Communication.print_play_output(
            key='Side A', value=f'{flashcard["side_a"]}'
        )
        start_time = datetime.now()
        side_b = Communication.print_play_input(key='Side B')
        end_time = datetime.now()
        is_timeout = (end_time - start_time) > timedelta(
            seconds=self.config.getint('play', 'answer_timeout')
        )

        side_b = self.normalize_sentence(side_b)
        flashcard_side_b = self.normalize_sentence(flashcard['side_b'])

        return side_b, flashcard_side_b, is_timeout

    def handle_answer(self, flashcard, side_b, flashcard_side_b, is_timeout):
        if side_b == flashcard_side_b:
            if is_timeout:
                result = TermColor.red('Timeout')
                box = 0
                self.timeout += 1
            else:
                result = TermColor.green('Right')
                box = flashcard['box'] + 1
                self.right += 1
        else:
            result = TermColor.red('Wrong')
            box = 0
            self.wrong += 1

        due = datetime.now() + timedelta(days=2**box)
        self.db_session.update_flashcard(
            due=due, box=box, flashcard_id=flashcard['id']
        )
        return result

    @staticmethod
    def print_result(flashcard, result):
        Communication.print_play_output(
            key='Answer',
            value=f'{flashcard["side_b"]} {result}'
        )
        Communication.print_play_output(
            key='Source',
            value=f'{flashcard["source"] or ""}'
        )
        Communication.print_play_output(
            key='Phonetic transcriptions',
            value=f'{flashcard["phonetic_transcriptions"] or ""}'
        )
        Communication.print_play_output(
            key='Explanation',
            value=f'{flashcard["explanation"] or ""}'
        )
        Communication.print_play_output(
            key='Examples',
            value=f'{flashcard["examples"] or ""}'
        )

    def print_end(self, with_start_new_line=False):
        Communication.print_output(
            f'Total: {self.total}, '
            f'Played: {self.played}, '
            f'Right: {self.right}, '
            f'Wrong: {self.wrong}, '
            f'Timeout: {self.timeout}',
            f'Game is over!',
            with_start_new_line=with_start_new_line
        )


class AddFlashcard(BaseClass):
    source = None

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.db_session = DBSession(self.config['database'].get('name'))

    def __call__(self, *args, **kwargs):
        Communication.print_output(TermColor.bold('Add new flashcard:'))
        side_a = Communication.print_input('Side A')
        side_b = Communication.print_input('Side B')
        source = Communication.print_input('Source')
        if source.strip() == '\p':
            source = self.__class__.source
        else:
            self.__class__.source = source

        phonetic_transcriptions = Communication.print_input(
            'Phonetic transcriptions'
        )
        part_of_speech = Communication.print_input('Part of speech')
        explanation = Communication.print_input('Explanation')
        explanation = f'[{part_of_speech}] {explanation}'
        examples = Communication.print_input('Examples(;)')

        # side_a = self.normalize_sentence(side_a)
        # side_b = self.normalize_sentence(side_b)
        side_a = self.remove_whitespaces(side_a)
        side_b = self.remove_whitespaces(side_b)

        duplicates = self.db_session.get_duplicates(
            user_id=self.user_id, side_a=side_a, side_b=side_b
        )
        self.show_duplicates(duplicates)

        box = 0
        due = datetime.now() + timedelta(days=2**box)

        action = self.request_input(
            request_answers=('y', 'n'),
            request_msgs=[
                (
                    TermColor.bold('Adding flashcard'),
                    f'{TermColor.ligth_blue("Side A:")} {side_a}',
                    f'{TermColor.ligth_blue("Side B:")} {side_b}',
                    f'{TermColor.ligth_blue("Box:")} {box}',
                    f'{TermColor.ligth_blue("Due:")} {due}',
                    f'{TermColor.ligth_blue("Source:")} {source}',
                    f'{TermColor.ligth_blue("Phonetic transcriptions:")} '
                    f'{phonetic_transcriptions}',
                    f'{TermColor.ligth_blue("Explanation:")} {explanation}',
                    f'{TermColor.ligth_blue("Examples:")} {examples}'
                ),
                (
                    f'Duplicates: {len(duplicates)}',
                    f'Do you want to add '
                    f'[{TermColor.green("y")}/{TermColor.red("n")}] ?',
                )
            ]
        )

        if action == 'y':
            flashcard = {
                'user_id': self.user_id,
                'side_a': side_a,
                'side_b': side_b,
                'box': box,
                'due': due,
                'source': source,
                'explanation': explanation,
                'examples': examples,
                'phonetic_transcriptions': phonetic_transcriptions

            }
            self.db_session.add_flashcard(flashcard=flashcard)
            Communication.print_output(
                TermColor.bold(f'Added: [{side_a}] / [{side_b}]')
            )
        else:
            Communication.print_output(
                TermColor.red('Aborting flashcard.')
            )

    @staticmethod
    def show_duplicates(duplicates):
        if duplicates:
            Communication.print_output(
                TermColor.bold(f'Duplicate flashcards: {len(duplicates)}')
            )
            for duplicate in duplicates:
                Communication.print_output(
                    f'Side A: {duplicate["side_a"]}',
                    f'Side B: {duplicate["side_b"]}',
                    f'Box: {duplicate["box"]}',
                    f'Due: {duplicate["due"]}',
                    f'User: {duplicate["user_id"]}',
                    f'Source: {duplicate["source"]}',
                    f'Created: {duplicate["created"]}'
                )


if __name__ == '__main__':
    SpacedRehearsal().run()
