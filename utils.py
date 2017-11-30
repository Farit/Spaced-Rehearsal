import re
import time
import datetime
import string


class TermColor:
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    LIGTH_BLUE = '\033[1;34m'
    PURPLE = '\033[35m'
    GREY = '\033[1;30m'
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
    def grey(cls, string_to_color):
        return cls.coloralize(cls.GREY, string_to_color)

    @classmethod
    def ligth_blue(cls, string_to_color):
        return cls.coloralize(cls.LIGTH_BLUE, string_to_color)

    @classmethod
    def bold(cls, string_to_color):
        return cls.coloralize(cls.BOLD, string_to_color)

    @classmethod
    def underline(cls, string_to_color):
        return cls.coloralize(cls.UNDERLINE, string_to_color)


class Communication:

    @classmethod
    def print_input(cls, str_msg):
        return input(TermColor.grey(f'[{str_msg}] ->: '))

    @classmethod
    def print_action(cls):
        return input(TermColor.grey(f'[Action] ->: '))

    @classmethod
    def print_output(cls, *str_msgs, with_start_new_line=False):
        sep = '\n...: '
        start_new_line = '\n' if with_start_new_line else ''
        print(f'{start_new_line}...:')
        print(f'...: {sep.join(str_msgs)}')

    @classmethod
    def print_play_output(cls, key, value):
        key = TermColor.grey(f'{key}: ')
        return print(f">>>> {key}{value}")

    @classmethod
    def print_play_input(cls, key):
        key = TermColor.grey(f'{key}: ')
        return input(f">>>> {key}")


def datetime_now():
    local_tz = datetime.timezone(datetime.timedelta(seconds=-time.timezone))
    return datetime.datetime.now(tz=local_tz)


def datetime_utc_now():
    now = datetime_now()
    utc_now = (now - now.utcoffset()).replace(tzinfo=datetime.timezone.utc)
    return utc_now


def normalize_value(value):
    _normalized = ''
    for word in value.split(' '):
        word = word.strip()
        if word:
            prefix = f' ' if word not in string.punctuation else f''
            _normalized += prefix + word
    return _normalized.strip()


def remove_whitespaces(value):
    return re.sub(r'[\s]{2,}', r' ', value).strip()

