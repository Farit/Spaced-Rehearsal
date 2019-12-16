import re
import sys
import logging
import readline
import textwrap
import shutil
import asyncio

from functools import partial

from src.formatting import Formatting

logger = logging.getLogger(__name__)


class AsyncStdIO:
    wait_timeout = 0.01

    def __init__(self):
        self.loop = None
        self.queue = asyncio.Queue()
        self.formatting = Formatting()
        self.ansi_escape_codes = re.compile(r'(\x1B\[[0-?]*[ -/]*[@-~])')

    def set_loop(self, loop):
        self.loop = loop

    def handle_stdout(self, msg):
        sys.stdout.buffer.write(msg.encode('utf-8'))
        sys.stdout.flush()
        self.loop.remove_writer(sys.stdout)

    @staticmethod
    def blocking_input(prompt, pre_fill='', history=None):
        pre_fill = '' if pre_fill is None else pre_fill
        def startup_hook():
            readline.insert_text(pre_fill)

            if history is not None:
                readline.clear_history()
                _history = (
                    history if isinstance(history, list) else [str(history)]
                )
                for line in _history:
                    readline.add_history(str(line))

        readline.set_startup_hook(startup_hook)
        try:
            return input(prompt)
        finally:
            readline.set_startup_hook()

    @staticmethod
    def get_terminal_width():
        terminal_size = shutil.get_terminal_size()
        left_margin = 10
        terminal_width = terminal_size[0] - left_margin
        return terminal_width

    def ansi_text_generator(self, ansi_text):
        """
        Iterates ANSI text by characters.

        ANSI control codes treated as a whole single character.
        These codes affect color and display style, but they have no logical
        length.

        Example:
            ansi_text = '\x1b[32mW\x1b[0mithin a few years'

            The result of calling the ansi_text_generator:

            [
                ('\x1b[32m', 'ansi_esc'),
                ('W', 'regular'),
                ('\x1b[0m', 'ansi_esc'),
                ('i', 'regular')
                ('t', 'regular')
                ...
            ]

        """

        for item in re.split(self.ansi_escape_codes, ansi_text):
            if not item:
                continue

            # ANSI escape sequence.
            if re.match(self.ansi_escape_codes, item):
                yield (item, 'ansi_esc')
                continue

            # Regular symbol.
            for i in item:
                yield (i, 'regular')

    async def print(self, *msgs, bottom_margin=0):
        ansi_wrapped_lines = []

        for msg in msgs:
            raw_text = ''.join(
                char
                for char, char_type in self.ansi_text_generator(msg)
                if char_type == 'regular'
            )

            raw_wrapped_text = textwrap.wrap(
                raw_text, width=self.get_terminal_width()
            )

            ansi_text_gen = self.ansi_text_generator(msg)

            for raw_wrapped_line in raw_wrapped_text:
                raw_wrapped_line_gen = (i for i in raw_wrapped_line)

                ansi_wrapped_line = []

                raw_wrapped_line_sym = next(raw_wrapped_line_gen, None)
                while True:
                    if raw_wrapped_line_sym is None:
                        break

                    ansi_text_sym, ansi_sym_type = next(
                        ansi_text_gen, (None, None)
                    )

                    if ansi_text_sym is not None:
                        ansi_wrapped_line.append((ansi_text_sym, ansi_sym_type))

                    if raw_wrapped_line_sym == ansi_text_sym:
                        raw_wrapped_line_sym = next(raw_wrapped_line_gen, None)

                ansi_wrapped_lines.append(ansi_wrapped_line)

            while True:
                ansi_text_sym, ansi_sym_type = next(
                    ansi_text_gen, (None, None)
                )
                if ansi_text_sym is None:
                    break
                ansi_wrapped_lines[-1].append((ansi_text_sym, ansi_sym_type))

        last_ansi_esp_control = ''
        message = self.formatting.white(f'...: ', is_escape_seq=True)
        for ind, ansi_line in enumerate(ansi_wrapped_lines, start=1):
            msg = ''
            for char, char_type in ansi_line:
                if char_type == 'ansi_esc':
                    last_ansi_esp_control = char
                msg += char

            message += msg
            if ind != len(ansi_wrapped_lines):
                message += self.formatting.white(f'\n...: ', is_escape_seq=True)
                message += last_ansi_esp_control

        for _ in range(bottom_margin):
            message += self.formatting.white(f'\n...: ', is_escape_seq=True)

        message = f'{message}\n'

        self.loop.add_writer(
            sys.stdout, partial(self.handle_stdout, message)
        )
        await asyncio.sleep(self.wait_timeout)

    async def input(self, msg, pre_fill='', history=None):
        message = self.formatting.grey(f'[{msg}] ->: ', is_escape_seq=True)
        future = self.loop.run_in_executor(
            None, self.blocking_input, message, pre_fill, history
        )

        try:
            result = await future
        except EOFError:
            self.loop.add_writer(
                sys.stdout, partial(self.handle_stdout, '\n')
            )
            await asyncio.sleep(self.wait_timeout)
            raise

        return result.strip()

    async def input_action(self, action_msgs, action_answers):
        action = None
        while action not in action_answers:
            await self.print(*action_msgs)
            if action is not None:
                msg = self.formatting.red(f'Invalid command: {action}')
                await self.print(msg)

            action = await self.input('Action')
            action = action.lower()

        return action
