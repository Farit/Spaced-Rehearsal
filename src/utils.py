import re
import sys
import time
import math
import datetime
import string
import logging
import doctest


def normalize_eng_word(word):
    """
    Returns normalized word containing only lower case letters. 
    Correctly handles compound word with a hyphen.
    >>> print(normalize_eng_word('book.,'))
    book
    >>> print(normalize_eng_word('NON-SMOKING ?'))
    non-smoking
    >>> print(normalize_eng_word('table-'))
    table
    >>> print(normalize_eng_word('-chair'))
    chair
    >>> print(normalize_eng_word('- . co-workers !?  '))
    co-workers
    >>> print(normalize_eng_word(" 5 o'clock"))
    o'clock
    """
    return re.sub(r"(^-|-$|[^'a-z-]*)", '', word.lower())


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
    if datetime_obj.utcoffset() is not None:
        datetime_obj = datetime_obj - datetime_obj.utcoffset()
    in_utc = datetime_obj.replace(tzinfo=datetime.timezone.utc)

    offset = offset if offset >= 0 else -offset
    to_tz = datetime.timezone(datetime.timedelta(seconds=offset))
    return (in_utc + datetime.timedelta(seconds=offset)).replace(tzinfo=to_tz)


def convert_datetime_to_local(datetime_obj: datetime):
    if datetime_obj is not None:
        return datetime_change_timezone(datetime_obj, offset=time.timezone)


def normalize_text(text):
    """
    >>> print(normalize_text('Where are the t-shirts?'))
    where are the t-shirts
    >>> print(normalize_text("The plane departs at 5 o'clock in the evening."))
    the plane departs at 5 o'clock in the evening
    >>> print(normalize_text("And people vary, too, in their susceptibility to addiction."))
    and people vary too in their susceptibility to addiction
    >>> print(normalize_text("The phone bill hasn't come yet."))
    the phone bill hasn't come yet
    """
    text = text or ''
    text = remove_whitespaces(text)
    text = text.lower()

    words = []
    for word in text.split():
        if not word.isnumeric():
            words.append(normalize_eng_word(word))
        else:
            words.append(word)
    return ' '.join(words)


def normalize_value(value, *, remove_trailing=None, to_lower=False):
    _normalized = ''
    for word in (value or '').split(' '):
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


def get_human_readable_file_size(size_bytes):
    if not isinstance(size_bytes, int):
        return

    if size_bytes == 0:
        return "0B"

    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


class StreamStdOutHandler(logging.StreamHandler):
    def __init__(self):
        super().__init__(stream=sys.stdout)
        self.addFilter(lambda record: record.levelno < logging.WARN)


class StreamStdErrorHandler(logging.StreamHandler):
    def __init__(self):
        super().__init__(stream=sys.stderr)
        self.addFilter(lambda record: record.levelno >= logging.WARN)


# The dictionary of base configuration information.
# Clients may add additional information or overwrite existing one before
# passing it to the logging.config.dictConfig() function
# https://docs.python.org/3/library/logging.config.html#logging.config.dictConfig
log_config_as_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    # root logger
    'root': {
        'level': 'NOTSET',
        'handlers': ['file'],
    },
    'formatters': {
        'default': {
            'format': (
                '[%(asctime)s] (%(pathname)s:%(lineno)d) '
                '%(levelname)s# %(name)s:: %(message)s'
            ),
        },
        'simple': {
            'format': (
                '[%(asctime)s] %(levelname)s# %(message)s'
            ),
        },
        'precise': {
            'format': (
                '[%(asctime)s] [%(process)d:%(threadName)s] [%(levelname)s] '
                '[%(name)s] {%(pathname)s:%(lineno)d} %(message)s'
            )

        }
    },
    'handlers': {
        'console_stdout_default': {
            '()': StreamStdOutHandler,
            'formatter': 'default',
            'level': 'DEBUG'
        },
        'console_stderr_default': {
            '()': StreamStdErrorHandler,
            'formatter': 'default',
        },
        'console_stdout_simple': {
            '()': StreamStdOutHandler,
            'formatter': 'simple',
            'level': 'DEBUG'
        },
        'console_stderr_simple': {
            '()': StreamStdErrorHandler,
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'precise',
            'filename': '/tmp/spaced_rehearsal.log',
        }
    },
    # Add here you custom loggers or specify logging for third-party modules.
    'loggers': {
        # Example of configuration of the python "tornado" module logging
        # 'tornado': {
        #     'handlers': ['file'],
        #     'level': 'INFO'
        # },
        'terminal_utility': {
            'level': 'DEBUG',
            'propagate': False,
            'handlers': ['console_stdout_default', 'console_stderr_default'],
        },
    }
}


if __name__ == '__main__':
    doctest.testmod(verbose=True)
