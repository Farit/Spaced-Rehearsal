#!/usr/bin/env python3.6

import random
import string
import sqlite3
import signal
import asyncio
import functools
import configparser

from datetime import datetime, timedelta

from utils import TermColor, Communication, handle_eof


class BaseClass:

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.cfg')

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
        return action

    @staticmethod
    def zip_row(row):
        return {k: row[k] for k in row.keys()}


class SpacedRehearsal(BaseClass):

    def __init__(self):
        super().__init__()
        self.loop = asyncio.get_event_loop()
        self.db_conn = None
        self.db_cursor = None
        self.user = None
        self.set_signal_handler('sigint')
        self.set_signal_handler('sigterm')

    def run(self):
        try:
            self.loop.call_soon(self.setup_db)
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
        self.db_conn.close()
        self.loop.stop()

    def setup_db(self):
        self.db_conn = sqlite3.connect('spaced_rehearsal.db')
        self.db_conn.row_factory = sqlite3.Row
        self.db_cursor = self.db_conn.cursor()

        with open('sql/users.sql') as fh:
            users_table = fh.read()
        self.db_cursor.execute(users_table)
        self.db_conn.commit()

        with open('sql/flashcards.sql') as fh:
            flashcards_sql = fh.read()
        self.db_cursor.executescript(flashcards_sql)
        self.db_conn.commit()

        self.loop.call_soon(self.login)

    @handle_eof('quit')
    def login(self):
        login_name = Communication.print_input('Login')
        query = self.db_cursor.execute(
            'select * from users where login=?', (login_name,)
        ).fetchone()
        if query is None:
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
            self.user = self.zip_row(row=query)
            self.loop.call_soon(self.choose_action)

    def register(self, login_name):
        self.db_cursor.execute(
            'insert into users(login) values (?);',
            (login_name, )
        )
        self.db_conn.commit()
        Communication.print_output(f'User {login_name} is registered!')
        self.loop.call_soon(self.login)

    @handle_eof('choose_action')
    def choose_action(self):
        ready_flashcards = self.get_ready_flashcards()
        action = self.request_input(
            request_answers=('a', 'p', 'q'),
            request_msgs=[
                (
                    f'Do you want to {TermColor.yellow("add")} '
                    f'[{TermColor.yellow("a")}] or to {TermColor.green("play")}'
                    f'[{TermColor.green("p")}] ?',
                    f'Number of the flashcards: {self.count_flashcards()}',
                    f'Number of the flashcards ready to play: '
                    f'{len(ready_flashcards)}',
                    f'If you want to {TermColor.red("quit")}, please type '
                    f'[{TermColor.red("q")}].'
                )
            ]
        )
        action = {'a': 'add', 'p': 'play', 'q': 'quit'}[action]
        getattr(self, action)()

    def get_ready_flashcards(self):
        query = self.db_cursor.execute(
            'select * from flashcards where user_id = ? and due <= ?',
            (self.user['id'], datetime.now())
        )
        flashcards = []
        for row in query:
            flashcard = self.zip_row(row=row)
            flashcards.append(flashcard)
        return flashcards

    def count_flashcards(self):
        query = self.db_cursor.execute(
            'select count(*) from flashcards where user_id = ?',
            (self.user['id'],)
        )
        return query.fetchone()['count(*)']

    @handle_eof('choose_action')
    def play(self):
        flashcards = self.get_ready_flashcards()
        Play(self.db_conn, self.db_cursor)(flashcards)
        self.loop.call_soon(self.choose_action)

    @handle_eof('choose_action')
    def add(self):
        AddFlashcard(self.db_conn, self.db_cursor, self.user['id'])()
        self.loop.call_soon(self.choose_action)

    def quit(self):
        self.exit('sigterm')


class Play(BaseClass):

    def __init__(self, db_conn, db_cursor):
        super().__init__()
        self.total = 0
        self.count = 0
        self.played = 0
        self.right = 0
        self.wrong = 0
        self.timeout = 0
        self.db_conn = db_conn
        self.db_cursor = db_cursor

    def __call__(self, flashcards):
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
            TermColor.bold(f'Flashcard {self.count}/{self.total}')
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
        self.db_cursor.execute(
            'update flashcards set due=?, box=? where id=?',
            (due, box, flashcard['id'])
        )
        self.db_conn.commit()
        return result

    @staticmethod
    def print_result(flashcard, result):
        Communication.print_play_output(
            key='Answer',
            value=f'{flashcard["side_b"]} {result}'
        )
        Communication.print_play_output(
            key='Source',
            value=f'{flashcard["source"]}'
        )
        Communication.print_play_output(
            key='Phonetic transcriptions',
            value=f'{flashcard["phonetic_transcriptions"]}'
        )
        Communication.print_play_output(
            key='Comments',
            value=f'{flashcard["comments"]}'
        )

    def print_end(self):
        Communication.print_output(
            f'Total: {self.total}, '
            f'Played: {self.played}, '
            f'Right: {self.right}, '
            f'Wrong: {self.wrong}, '
            f'Timeout: {self.timeout}',
            f'Game is over!',
        )


class AddFlashcard(BaseClass):

    def __init__(self, db_conn, db_cursor, user_id):
        super().__init__()
        self.db_conn = db_conn
        self.db_cursor = db_cursor
        self.user_id = user_id

    def __call__(self, *args, **kwargs):
        Communication.print_output(TermColor.bold('Add new flashcard:'))
        side_a = Communication.print_input('Side A')
        side_b = Communication.print_input('Side B')
        source = Communication.print_input('Source')
        phonetic_transcriptions = Communication.print_input(
            'Phonetic transcriptions'
        )
        comments = Communication.print_input('Comments')

        side_a = self.normalize_sentence(side_a)
        side_b = self.normalize_sentence(side_b)

        duplicates = self.get_duplicates(side_a, side_b)

        if not duplicates:
            box = 0
            due = datetime.now() + timedelta(days=2**box)

            action = self.request_input(
                request_answers=('y', 'n'),
                request_msgs=[
                    (
                        TermColor.bold('Adding flashcard'),
                        f'{TermColor.ligth_blue("Side A:")} {side_a}',
                        f'{TermColor.ligth_blue("Side B")} {side_b}',
                        f'{TermColor.ligth_blue("Box:")} {box}',
                        f'{TermColor.ligth_blue("Due:")} {due}',
                        f'{TermColor.ligth_blue("Source:")} {source}',
                        f'{TermColor.ligth_blue("Phonetic transcriptions:")} '
                        f'{phonetic_transcriptions}',
                        f'{TermColor.ligth_blue("Comment:")} {comments}'
                    ),
                    (
                        f'Do you want to add '
                        f'[{TermColor.green("y")}/{TermColor.red("n")}] ?',
                    )
                ]
            )

            if action == 'y':
                self.db_cursor.execute(
                    'insert into flashcards'
                    '(user_id, side_a, side_b, box, due, source, comments, '
                    ' phonetic_transcriptions)'
                    'values (?, ?, ?, ?, ?, ?, ?, ?);',
                    (self.user_id, side_a, side_b, box, due, source,
                     comments, phonetic_transcriptions)
                )
                self.db_conn.commit()
                Communication.print_output(
                    TermColor.bold(f'Added: [{side_a}] / [{side_b}]')
                )
            else:
                Communication.print_output(
                    TermColor.red('Aborting flashcard.')
                )

        else:
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

    def get_duplicates(self, side_a, side_b):
        query = self.db_cursor.execute(
            'select * from flashcards '
            'where (side_a = ? or side_b = ?) and user_id = ?',
            (side_a, side_b, self.user_id)
        )
        duplicates = []
        for row in query:
            duplicate = self.zip_row(row=row)
            duplicates.append(duplicate)

        return duplicates


if __name__ == '__main__':
    SpacedRehearsal().run()
