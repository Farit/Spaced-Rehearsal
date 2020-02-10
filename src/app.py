#!/usr/bin/env python3.6

import logging
import signal
import asyncio


from web_app.app import Application as WebApp

logger = logging.getLogger(__name__)


class SpacedRehearsal:

    def __init__(self, mediator):
        self.loop = asyncio.get_event_loop()
        self.mediator = mediator
        self.web_app = WebApp(flashcard_type=self.mediator.name())
        self.set_signal_handler(signal.SIGINT)
        self.set_signal_handler(signal.SIGTERM)

    def run(self):
        try:
            self.web_app.start()
            self.mediator.set_loop(self.loop)
            self.create_task(self.start())
            self.loop.run_forever()
        finally:
            self.loop.close()

    def set_signal_handler(self, signame):
        if signame == signal.SIGINT:
            self.loop.add_signal_handler(
                signame,
                lambda: self.create_task(self.mediator.set_sigint_handler())
            )
        else:
            self.loop.add_signal_handler(signame, lambda: None)

    def create_task(self, coroutine):
        task = asyncio.ensure_future(
            self.handle_exception(coroutine),
            loop=self.loop
        )

    async def handle_exception(self, coro):
        try:
            await coro
        except Exception as err:
            logging.exception(err)
            print(f'Error: {err}')
            self.loop.stop()

    async def start(self):
        await self.mediator.print(
            f'Web server is running on '
            f'http://{self.web_app.address}:{self.web_app.port}',
            bottom_margin=1
        )
        self.create_task(self.login())

    async def exit(self, signame='sigterm'):
        await self.mediator.print(
            f'Got signal {self.mediator.format_bold(f"{signame}")}',
            f'{self.mediator.format_red("Exit")}'
        )
        await self.mediator.exit()
        self.loop.stop()

    async def login(self):
        try:
            await self.mediator.print(
                'Please, enter a username.',
                bold=True
            )
            await self.mediator.print(
                f'In case if requested user does not exist '
                f'program will ask confirmation to create it. ',

                f'Pressing {self.mediator.format_red("Ctrl+D")} '
                f'terminates the program.'
            )

            while True:
                login_name = await self.mediator.input('Login')
                login_name = login_name.strip().lower()
                is_user_logged = await self.mediator.login_user(login_name)

                if is_user_logged:
                    self.web_app.set_user_id(self.mediator.get_user_id())
                    self.create_task(self.choose_action())
                    break

                action = await self.mediator.input_action(
                    action_answers=('y', 'n', 'q'),
                    action_msgs=[
                        self.mediator.format_bold(
                            f'A user with a login "{login_name}" '
                            f'does not exist.'
                        ),

                        f'Do you want to create it?',
                        f'Please, enter '
                        f'{self.mediator.format_green("y")} for YES or '
                        f'{self.mediator.format_red("n")} for NO',

                        f'Entering {self.mediator.format_red("q")} '
                        f'terminates the program.'
                    ]
                )

                if action == 'q':
                    self.create_task(self.exit())
                    break

                if action == 'y':
                    await self.mediator.register_user(login_name)

        except EOFError:
            await self.mediator.print('Termination!', red=True)
            self.create_task(self.exit())

    async def choose_action(self):
        try:
            total_number = await self.mediator.count_total_flashcards()
            review_number = await self.mediator.count_review_flashcards()

            await self.mediator.print(
                f'Number of the text flashcards: '
                f'{self.mediator.format_bold(total_number["text"])}',
                f'Number of the audio flashcards: '
                f'{self.mediator.format_bold(total_number["audio"])}',
                f'Number of the text flashcards ready to review: '
                f'{self.mediator.format_bold(review_number["text"])}',
                f'Number of the audio flashcards ready to review: '
                f'{self.mediator.format_bold(review_number["audio"])}',
                bottom_margin=1
            )

            action = await self.mediator.input_action(
                action_answers=('r', 'c', 'a', 's', 'd', 'q'),
                action_msgs=[
                    f'If you want to '
                    f'{self.mediator.format_green("review")}, '
                    f'{"please enter".rjust(13)} '
                    f'{self.mediator.format_green("r")}',

                    f'If you want to '
                    f'{self.mediator.format_yellow("create")}, '
                    f'{"please enter".rjust(13)} '
                    f'{self.mediator.format_yellow("c")}',

                    f'If you want to '
                    f'{self.mediator.format_light_blue("alter")}, '
                    f'{"please enter".rjust(14)} '
                    f'{self.mediator.format_light_blue("a")}',

                    f'If you want to '
                    f'{self.mediator.format_purple("search")}, '
                    f'{"please enter".rjust(13)} '
                    f'{self.mediator.format_purple("s")}',

                    f'If you want to '
                    f'{self.mediator.format_red("delete")}, '
                    f'{"please enter".rjust(13)} '
                    f'{self.mediator.format_red("d")}',

                    f'',

                    f'If you want to '
                    f'{self.mediator.format_grey("quit")}, '
                    f'{"please enter".rjust(15)} '
                    f'{self.mediator.format_grey("q")}'
                ]
            )
            if action == 'q':
                self.create_task(self.exit())
                return

            action_names = {
                'c': 'create',
                'd': 'delete',
                'a': 'alter',
                's': 'search',
                'r': 'review'
            }

            self.create_task(
                self.launch_action(action_name=action_names[action])
            )

        except EOFError:
            await self.mediator.print('Termination!', red=True)
            self.create_task(self.choose_action())

    async def launch_action(self, action_name):
        try:
            action_name = action_name.lower()

            if action_name == 'create':
                await self.mediator.launch_create_action()
            elif action_name == 'delete':
                await self.mediator.launch_delete_action()
            elif action_name == 'alter':
                await self.mediator.launch_alter_action()
            elif action_name == 'search':
                await self.mediator.launch_search_action()
            elif action_name == 'review':
                await self.mediator.launch_review_action()
            else:
                raise Exception(f'Unknown action name "{action_name}"')

        except EOFError:
            await self.mediator.print(
                f'{action_name.capitalize()} action termination!',
                red=True,
                bottom_margin=1
            )
        except Exception as err:
            await self.mediator.print(
                'Internal Error!',
                red=True,
                bottom_margin=1
            )
            raise err
        finally:
            self.create_task(self.choose_action())
