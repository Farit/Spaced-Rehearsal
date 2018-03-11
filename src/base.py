import sys
import readline
import textwrap
import asyncio

from functools import partial

from src.utils import TermColor


class AsyncIO:
    wait_timeout = 0.01

    def __init__(self, loop):
        self.loop = loop
        self.queue = asyncio.Queue()

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
        message = '\n...: ' + '\n...: '.join(msgs)
        message = f'...: {message}\n'
        self.loop.add_writer(
            sys.stdout, partial(self.handle_stdout, message)
        )
        await asyncio.sleep(self.wait_timeout)

    async def input(self, msg, pre_fill='', history=None):
        message = TermColor.grey(f'[{msg}] ->: ', is_escape_seq=True)
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
                await self.print(TermColor.red(f'Invalid command: {action}'))
            action = await self.input('Action')
            action = action.lower()

        return action

    async def print_formatted_output(self, output):
        formatted_output = []
        for line in output:
            output_lines = textwrap.wrap(line, width=100)
            for ind, output_line in enumerate(output_lines):
                if ind == 0:
                    formatted_output.append(output_line)
                else:
                    formatted_output.append(textwrap.indent(output_line, ' '*4))

        await self.print(*formatted_output)
