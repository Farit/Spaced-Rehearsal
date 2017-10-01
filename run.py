import signal
import asyncio
import functools


class TermColor:
    PURPLE = '\033[35m'
    BLUE = '\033[34m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @classmethod
    def coloralize(cls, color, string_to_color):
        return color + string_to_color + cls.END

    @classmethod
    def red(cls, string_to_color):
        return cls.coloralize(cls.RED, string_to_color)

    @classmethod
    def yellow(cls, string_to_color):
        return cls.coloralize(cls.YELLOW, string_to_color)
    
    @classmethod
    def green(cls, string_to_color):
        return cls.coloralize(cls.GREEN, string_to_color)

    @classmethod
    def bold(cls, string_to_color):
        return cls.coloralize(cls.BOLD, string_to_color)


class SpacedRehearsal:

    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.set_signal_handler('sigint')
        self.set_signal_handler('sigterm')

    def run(self):
        try:
            self.loop.call_soon(self.start)
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

    def start(self):
        action = None
        while action not in ('a', 'p', 'q'):
            prompt = (
                'Do you want to ' + TermColor.yellow('add') + ' [' +
                TermColor.yellow('a') + '] or to ' + TermColor.green('play') +
                '[' + TermColor.green('p') + ']?\n'
                'If you want to ' + TermColor.red('quit') +
                ', please type [' + TermColor.red('q') + '].\n'
            )
            if action is not None:
                prompt = TermColor.red(f'Invalid command: {action}\n') + prompt
            action = input(prompt)

        action = {'a': 'add', 'p': 'play', 'q': 'quit'}[action]
        getattr(self, f'action_{action}')()

    def action_play(self):
        print(f'action play')

    def action_add(self):
        print(f'action add')
    
    def action_quit(self):
        self.exit('sigterm')


if __name__ == '__main__':
    SpacedRehearsal().run()
