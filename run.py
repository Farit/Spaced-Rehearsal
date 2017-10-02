import signal
import asyncio
import functools

from utils import TermColor


class SpacedRehearsal:

    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.set_signal_handler('sigint')
        self.set_signal_handler('sigterm')

    def run(self):
        try:
            self.loop.call_soon(self.choose_action)
            self.loop.run_forever()
        finally:
            self.loop.close()

    def set_signal_handler(self, signame):
        self.loop.add_signal_handler(
            getattr(signal, signame.upper()),
            functools.partial(self.exit, signame)
        )

    def exit(self, signame):
        print(
            'Got signal ', TermColor.bold(f'"{signame}": '),
            TermColor.red('exit')
        )
        self.loop.stop()

    def choose_action(self):
        action = None
        while action not in ('a', 'p', 'q'):
            prompt = (
                'Do you want to ' + TermColor.yellow('add') + ' [' +
                TermColor.yellow('a') + '] or to ' + TermColor.green('play') +
                '[' + TermColor.green('p') + ']?\n'
                'If you want to ' + TermColor.red('quit') +
                ', please type [' + TermColor.red('q') + '].\nAction: '
            )
            if action is not None:
                prompt = TermColor.red(f'Invalid command: {action}\n') + prompt
            action = input(prompt)

        action = {'a': 'add', 'p': 'play', 'q': 'quit'}[action]
        getattr(self, f'action_{action}')()

    def action_play(self):
        print(f'action play')

    def action_add(self):
        print(TermColor.bold('\nAdding new item:'))
        side_a = input('Side A: ')
        side_b = input('Side B: ')
        print(TermColor.underline(f'Added: {side_a}/{side_b}'), '\n')
        self.loop.call_soon(self.choose_action)

    def action_quit(self):
        self.exit('sigterm')


if __name__ == '__main__':
    SpacedRehearsal().run()
