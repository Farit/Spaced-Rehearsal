import sys
import asyncio

from functools import partial

from utils import TermColor


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

        return result.rstrip('\n')

    async def input_action(self, action_msgs, action_answers):
        action = None
        while action not in action_answers:
            for action_msg in action_msgs:
                message = '\n...: ' + '\n...: '.join(action_msg)
                message = f'...: {message}\n'
                self.loop.add_writer(
                    sys.stdout, partial(self.handle_stdout, message)
                )
                await asyncio.sleep(self.wait_timeout)

            if action is not None:
                msg = TermColor.red(f'Invalid command: {action}\n')
                self.loop.add_writer(
                    sys.stdout, partial(self.handle_stdout, msg)
                )
                await asyncio.sleep(self.wait_timeout)

            msg = TermColor.grey(f'[Action] ->: ')
            self.loop.add_writer(
                sys.stdout, partial(self.handle_stdout, msg)
            )
            await asyncio.sleep(self.wait_timeout)

            self.loop.add_reader(sys.stdin, self.handle_stdin)
            action = await self.queue.get()
            if not action:
                self.loop.add_writer(
                    sys.stdout, partial(self.handle_stdout, '\n')
                )
                await asyncio.sleep(self.wait_timeout)
                raise EOFError()

            # action = action.rstrip('\n')
            action = action.strip()

        return action
