#!/usr/bin/env python3.6

import signal
import asyncio
import functools


from db_session import DBSession
from add import AddFlashcard
from play import Play
from utils import TermColor, Communication, datetime_now
from base import BaseClass


class SpacedRehearsal(BaseClass):

    def __init__(self):
        super().__init__()
        self.loop = asyncio.get_event_loop()
        self.db_session = DBSession(
            self.config['database'].get('name'), setup_db=True
        )
        self.user = None
        self.add_flashcard = None
        self.play_flashcards = None
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

    def login(self):
        try:
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
                self.add_flashcard = AddFlashcard(user_id=self.user['id'])
                self.play_flashcards = Play(user_id=self.user['id'])
                self.loop.call_soon(self.choose_action)

        except EOFError:
            Communication.print_output(
                TermColor.red('Termination!'),
                with_start_new_line=True
            )
        finally:
            self.loop.call_soon(self.quit)

    def register(self, login_name):
        self.db_session.register_user(login_name)
        Communication.print_output(f'User {login_name} is registered!')
        self.loop.call_soon(self.login)

    def choose_action(self):
        try:
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

        except EOFError:
            Communication.print_output(
                TermColor.red('Termination!'),
                with_start_new_line=True
            )
        finally:
            self.loop.call_soon(self.choose_action)

    def play(self):
        try:
            self.play_flashcards()
        except EOFError:
            self.play_flashcards.print_end(with_start_new_line=True)
            Communication.print_output(
                TermColor.red('Termination!'),
                with_start_new_line=False
            )
        finally:
            self.loop.call_soon(self.choose_action)

    def add(self):
        try:
            self.add_flashcard.add()
        except EOFError:
            Communication.print_output(
                TermColor.red('Termination!'),
                with_start_new_line=True
            )
        finally:
            self.loop.call_soon(self.choose_action)

    def quit(self):
        self.exit('sigterm')


if __name__ == '__main__':
    SpacedRehearsal().run()
