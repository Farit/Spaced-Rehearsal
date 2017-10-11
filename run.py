import string
import sqlite3
import signal
import asyncio
import functools

from datetime import datetime, timedelta

from utils import TermColor, Communication, handle_eof


class SpacedRehearsal:

    def __init__(self):
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
            action = None
            while action not in ('y', 'n', 'q'):
                Communication.print_output(
                    TermColor.red(f'User "{login_name}" does not exist.'),
                    'Do you want to create [y/n] ?',
                    f'If you want to {TermColor.red("quit")} '
                    f'please type [{TermColor.red("q")}].'
                )

                if action is not None:
                    Communication.print_output(
                        TermColor.red(f'Invalid command: {action}')
                    )

                action = Communication.print_action()

            action = {'y': 'register', 'n': 'login', 'q': 'quit'}[action]
            if action == 'register':
                self.register(login_name=login_name)
            else:
                getattr(self, action)()

        else:
            self.user = {k: query[k] for k in query.keys()}
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
        action = None
        while action not in ('a', 'p', 'q'):
            Communication.print_output(
                f'Do you want to {TermColor.yellow("add")} '
                f'[{TermColor.yellow("a")}] or to {TermColor.green("play")}'
                f'[{TermColor.green("p")}] ?',
                f'Number of the flashcards: {self.count_flashcards()}',
                f'Number of the flashcards ready to play: {len(ready_flashcards)}',
                f'If you want to {TermColor.red("quit")}, please type '
                f'[{TermColor.red("q")}].' 
            )

            if action is not None:
                Communication.print_output(
                    TermColor.red(f'Invalid command: {action}')
                )

            action = Communication.print_action()

        action = {'a': 'add', 'p': 'play', 'q': 'quit'}[action]
        getattr(self, action)()

    def get_ready_flashcards(self):
        query = self.db_cursor.execute(
            'select * from flashcards where user_id = ? and due <= ?',
            (self.user['id'], datetime.now())
        )
        flashcards = []
        for row in query:
            flashcard = {k: row[k] for k in row.keys()}
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
        count = 0
        right = 0
        wrong = 0
        timeout = 0
        for flashcard in flashcards:
            count += 1
            Communication.print_output(
                f'Flashcard {count}'
            )
            Communication.print_play_output(
                f'Side A: {flashcard["side_a"]}'
            )
            start_time = datetime.now()
            side_b = Communication.print_play_input('Side B')
            end_time = datetime.now()
            is_timeout = (end_time - start_time) > timedelta(seconds=20)

            side_b = self.normalize_sentence(side_b)
            flashcard_side_b = self.normalize_sentence(flashcard['side_b'])

            if side_b == flashcard_side_b:
                if is_timeout:
                    result = TermColor.red('Timeout')
                    box = 0
                    timeout += 1
                else:
                    result = TermColor.green('Right')
                    box = flashcard['box'] + 1
                    right += 1
            else:
                result = TermColor.red('Wrong')
                box = 0
                wrong += 1

            due = datetime.now() + timedelta(days=2**box)
            self.db_cursor.execute(
                'update flashcards set due=?, box=? where id=?',
                (due, box, flashcard['id'])
            )
            self.db_conn.commit()
            Communication.print_play_output(
                f'Answer: {flashcard["side_b"]} {result}'
            )

        Communication.print_output(
            f'Number of the flashcards ready to play: {len(flashcards)}',
            f'Number of the right answered flashcards: {right}',
            f'Number of the timeout answered flashcards: {timeout}',
            f'Number of the wrong answered flashcards: {wrong}',
            f'Game is over!',
        )
        self.loop.call_soon(self.choose_action)

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

    @handle_eof('choose_action')
    def add(self):
        Communication.print_output(TermColor.bold('Add new item:'))
        side_a = Communication.print_input('Side A')
        side_b = Communication.print_input('Side B')
        source = Communication.print_input('Source')

        side_a = self.normalize_sentence(side_a)
        side_b = self.normalize_sentence(side_b)

        query = self.db_cursor.execute(
            'select * from flashcards '
            'where (side_a = ? or side_b = ?) and user_id = ?',
            (side_a, side_b, self.user['id'])
        )
        duplicates = []
        for row in query:
            duplicate = {k: row[k] for k in row.keys()}
            duplicates.append(duplicate)

        if not duplicates:
            box = 0
            due = datetime.now() + timedelta(days=2**box)

            action = None
            while action not in ('y', 'n'):
                Communication.print_output(
                    TermColor.bold('Adding flashcard'),
                    f'{TermColor.ligth_blue("Side A:")} {side_a}',
                    f'{TermColor.ligth_blue("Side B")} {side_b}',
                    f'{TermColor.ligth_blue("Box:")} {box}',
                    f'{TermColor.ligth_blue("Due:")} {due}',
                    f'{TermColor.ligth_blue("Source:")} {source}',
                    f'Do you want to add '
                    f'[{TermColor.green("y")}/{TermColor.red("n")}] ?'
                )

                if action is not None:
                    Communication.print_output(
                        TermColor.red(f'Invalid command: {action}')
                    )

                action = Communication.print_action()

            if action == 'y':
                self.db_cursor.execute(
                    'insert into flashcards'
                    '(user_id, side_a, side_b, box, due, source)'
                    'values (?, ?, ?, ?, ?, ?);',
                    (self.user['id'], side_a, side_b, box, due, source)
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

        self.loop.call_soon(self.choose_action)

    def quit(self):
        self.exit('sigterm')


if __name__ == '__main__':
    SpacedRehearsal().run()
