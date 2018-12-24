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

    def set_loop(self, loop):
        self.loop = loop

    def handle_stdout(self, msg):
        sys.stdout.buffer.write(msg.encode('utf-8'))
        sys.stdout.flush()
        self.loop.remove_writer(sys.stdout)

    @staticmethod
    def blocking_input(prompt, pre_fill='', history=None):
        def startup_hook():
            readline.insert_text(pre_fill)

            if history is not None:
                readline.clear_history()
            for line in history or []:
                readline.add_history(line)

        readline.set_startup_hook(startup_hook)
        try:
            return input(prompt)
        finally:
            readline.set_startup_hook()

    async def print(self, *msgs):
        formatted_msgs = []
        terminal_size = shutil.get_terminal_size()
        width = terminal_size[0] - 10
        for msg in msgs:
            msg = str(msg)
            if len(msg) > 1:
                output_lines = textwrap.wrap(msg, width=width)
                for ind, output_line in enumerate(output_lines):
                    if ind != 0:
                        output_line = textwrap.indent(output_line, ' '*4)
                    formatted_msgs.append(output_line)
            else:
                formatted_msgs.append(msg)

        message = '...: ' + '\n...: '.join(formatted_msgs)
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

