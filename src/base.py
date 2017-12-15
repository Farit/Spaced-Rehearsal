import sys
import readline
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
    def blocking_input(prompt, pre_fill=''):
        readline.set_startup_hook(lambda: readline.insert_text(pre_fill))
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

    async def input(self, msg, pre_fill=''):
        message = TermColor.grey(f'[{msg}] ->: ')
        future = self.loop.run_in_executor(
            None, self.blocking_input, message, pre_fill
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

        return action
