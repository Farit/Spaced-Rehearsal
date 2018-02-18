#!/usr/bin/env python3.6

import signal
import asyncio


from src.config import ConfigAdapter
from src.db_session import DBSession
from src.add import AddFlashcard
from src.play import Play
from src.utils import TermColor, datetime_utc_now
from src.base import AsyncIO
from web_server.web_server import WebServer


class SpacedRehearsal:

    def __init__(self):
        self.user = None
        self.add_flashcard: AddFlashcard = None
        self.play_flashcards: Play = None
        self.loop = asyncio.get_event_loop()
        self.async_io = AsyncIO(loop=self.loop)
        self.config = ConfigAdapter(filename='config.cfg')
        self.db_session = DBSession(
            self.config['database'].get('name'), setup_db=True
        )
        self.web_server = None
        self.set_signal_handler('sigint')
        self.set_signal_handler('sigterm')

    def run(self):
        try:
            self.web_server = self.loop.run_until_complete(
                self.loop.create_server(
                    WebServer,
                    self.config['server'].get('host'),
                    self.config['server'].getint('port')
                )
            )
            asyncio.ensure_future(self.login(), loop=self.loop)
            self.loop.run_forever()
        finally:
            self.loop.close()

    def set_signal_handler(self, signame):
        self.loop.add_signal_handler(
            getattr(signal, signame.upper()),
            lambda: None
        )

    async def exit(self, signame='sigterm'):
        await self.async_io.print(
            f'Got signal {TermColor.bold(f"{signame}")}',
            f'{TermColor.red("Exit")}'
        )
        if self.user:
            await self.async_io.print(f'Bye {self.user["login"]}!')
        self.db_session.close()
        self.loop.stop()

    async def login(self):
        try:
            address, port = self.web_server.sockets[0].getsockname()
            WebServer.set_app()
            await self.async_io.print(
                f'Web server is running on http://{address}:{port}'
            )
            await self.async_io.print(
                TermColor.bold(f'Please, enter a username.'),
                f'In case if requested user does not exist program will ask '
                'confirmation to create it. ',
                f'Pressing {TermColor.red("Ctrl+D")} terminates the program.',
            )
            login_name = await self.async_io.input('Login')
            user = self.db_session.get_user(login_name)
            if user is None:
                action = await self.async_io.input_action(
                    action_answers=('y', 'n', 'q'),
                    action_msgs=[
                        TermColor.bold(
                            f'A user with a login "{login_name}" '
                            f'does not exist.'
                        ),
                        'Do you want to create it?',
                        f'Please, enter {TermColor.green("y")} for YES or '
                        f'{TermColor.red("n")} for NO',
                        f'Entering {TermColor.red("q")} terminates the program.'
                    ]
                )

                if action == 'y':
                    method = self.register(login_name)
                elif action == 'n':
                    method = self.login()
                else:
                    method = self.exit()

                asyncio.ensure_future(method, loop=self.loop)

            else:
                self.user = self.db_session.get_user(login_name)
                WebServer.set_user_id(user_id=self.user['id'])
                self.add_flashcard = AddFlashcard(
                    user_id=self.user['id'], async_io=self.async_io
                )
                self.play_flashcards = Play(
                    user_id=self.user['id'], async_io=self.async_io
                )
                asyncio.ensure_future(self.choose_action(), loop=self.loop)

        except EOFError:
            await self.async_io.print(TermColor.red('Termination!'))
            asyncio.ensure_future(self.exit(), loop=self.loop)

    async def register(self, login_name):
        self.db_session.register_user(login_name)
        await self.async_io.print(f'User {login_name} is registered!')
        asyncio.ensure_future(self.login(), loop=self.loop)

    async def choose_action(self):
        try:
            total_number = self.db_session.count_flashcards(
                user_id=self.user["id"]
            )
            ready_number = self.db_session.count_flashcards(
                user_id=self.user["id"],
                review_timestamp=datetime_utc_now()
            )
            action = await self.async_io.input_action(
                action_answers=('a', 'p', 'q'),
                action_msgs=[
                    f'Number of the flashcards: '
                    f'{TermColor.bold(str(total_number))}',
                    f'Number of the flashcards ready to play: '
                    f'{TermColor.bold(str(ready_number))}',
                    f'If you want to {TermColor.yellow("add")} a new flashcard,'
                    f' please enter {TermColor.yellow("a")}.',
                    f'If you want to {TermColor.green("play")},'
                    f' please enter {TermColor.green("p")}.',
                    f'If you want to {TermColor.red("quit")}, please enter '
                    f'{TermColor.red("q")}.'
                ]
            )
            if action == 'a':
                asyncio.ensure_future(self.add(), loop=self.loop)
            elif action == 'p':
                asyncio.ensure_future(self.play(), loop=self.loop)
            else:
                asyncio.ensure_future(self.exit(), loop=self.loop)

        except EOFError:
            await self.async_io.print(TermColor.red('Termination!'))
            asyncio.ensure_future(self.choose_action(), loop=self.loop)

    async def play(self):
        try:
            await self.play_flashcards.play()
        except EOFError:
            await self.play_flashcards.print_game_score()
            await self.async_io.print(TermColor.red('Termination!'))
        except Exception as err:
            await self.async_io.print(TermColor.red('Error!'))
            raise err
        finally:
            asyncio.ensure_future(self.choose_action(), loop=self.loop)

    async def add(self):
        try:
            await self.add_flashcard.add()
        except EOFError:
            self.add_flashcard.popleft_previous_sources()
            await self.async_io.print(TermColor.red('Termination!'))

        except Exception as err:
            self.add_flashcard.popleft_previous_sources()
            await self.async_io.print(TermColor.red('Error!'))
            raise err

        finally:
            asyncio.ensure_future(self.choose_action(), loop=self.loop)
