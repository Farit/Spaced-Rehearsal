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
    def purple(cls, string_to_color):
        return cls.coloralize(cls.PURPLE, string_to_color)

    @classmethod
    def ligth_blue(cls, string_to_color):
        return cls.coloralize(cls.LIGTH_BLUE, string_to_color)

    @classmethod
    def bold(cls, string_to_color):
        return cls.coloralize(cls.BOLD, string_to_color)

    @classmethod
    def underline(cls, string_to_color):
        return cls.coloralize(cls.UNDERLINE, string_to_color)


def datetime_now():
    offset = time.timezone
    offset = offset if offset >= 0 else -offset
    local_tz = datetime.timezone(datetime.timedelta(seconds=offset))
    return datetime.datetime.now(tz=local_tz)


def datetime_utc_now():
    now = datetime_now()
    utc_now = (now - now.utcoffset()).replace(tzinfo=datetime.timezone.utc)
    return utc_now


def datetime_change_timezone(datetime_obj, *, offset):
    assert isinstance(offset, (float, int)), f'received: {offset!r}'
    in_utc = (datetime_obj - datetime_obj.utcoffset()).replace(
        tzinfo=datetime.timezone.utc
    )

    offset = offset if offset >= 0 else -offset
    to_tz = datetime.timezone(datetime.timedelta(seconds=offset))
    return (in_utc + datetime.timedelta(seconds=offset)).replace(tzinfo=to_tz)


def normalize_value(value, *, remove_trailing=None, to_lower=False):
    _normalized = ''
    for word in value.split(' '):
        word = word.strip()
        if word:
            prefix = f' ' if word not in string.punctuation else f''
            _normalized += prefix + word

    if remove_trailing is not None:
        _normalized = _normalized.rstrip(remove_trailing)

    if to_lower:
        _normalized = _normalized.lower()

    return _normalized.strip()


def remove_whitespaces(value):
    return re.sub(r'[\s]{2,}', r' ', value).strip()

