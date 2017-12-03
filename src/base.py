import sys
import asyncio

from functools import partial

from src.utils import TermColor


class AsyncIO:
    wait_timeout = 0.01

    def __init__(self, loop):
        self.loop = loop
        self.queue = asyncio.Queue()

    def __call__(self, msg):
        self.loop.add_writer(sys.stdout, self.handle_stdout, msg)
        self.loop.add_reader(sys.stdin, self.handle_stdin)
        return self.queue.get()

    def handle_stdout(self, msg):
        sys.stdout.buffer.write(msg.encode('utf-8'))
        sys.stdout.flush()
        self.loop.remove_writer(sys.stdout)

    def handle_stdin(self):
        data = sys.stdin.readline()
        asyncio.async(self.queue.put(data))

    async def print(self, *msgs):
        message = '\n...: ' + '\n...: '.join(msgs)
        message = f'...: {message}\n'
        self.loop.add_writer(
            sys.stdout, partial(self.handle_stdout, message)
        )
        await asyncio.sleep(self.wait_timeout)

    async def input(self, msg):
        message = TermColor.grey(f'[{msg}] ->: ')
        self.loop.add_writer(
            sys.stdout, partial(self.handle_stdout, message)
        )
        await asyncio.sleep(self.wait_timeout)

        self.loop.add_reader(sys.stdin, self.handle_stdin)
        result = await self.queue.get()

        if not result:
            self.loop.add_writer(
                sys.stdout, partial(self.handle_stdout, '\n')
            )
            await asyncio.sleep(self.wait_timeout)
            raise EOFError()

        return result.strip()

    async def input_action(self, action_msgs, action_answers):
        action = None
        while action not in action_answers:
            await self.print(*action_msgs)
            if action is not None:
                await self.print(TermColor.red(f'Invalid command: {action}'))
            action = await self.input('Action')

        return action
