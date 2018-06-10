import re
import time
import datetime
import string

from functools import partial


class TermColorMetaClass(type):

    def __getattr__(cls, item):
        colours = [
            'red', 'yellow', 'blue', 'green', 'grey', 'purple', 'light_blue',
            'bold', 'underline'
        ]
        if item in colours:
            return partial(cls.to_colour, colour=item)
        return super().__getattribute__(item)


class TermColor(metaclass=TermColorMetaClass):
    """
    Why we need \001 and \002 escapes, answer provided from the
    https://bugs.python.org/issue20359:

    Thanks again for the responses and your help. After a bit of research,
    I discovered the /reasons/ behind needing the \001 and \002 escapes.
    Thought I'd log the links here for posterity sake:
      - To color something in on a color capable terminal console you just
        need to use the "\033[<color code>m" escape sequence.
        This would be sufficient[1]
      - However readline messes up the line width calculation because it
        measures the escape sequences as a characters too. To avoid this you
        have to wrap the escape sequences within \001 and \002.[2]
      - On some terminal applications (like the one I am using - terminator[3]),
        if you add the \001 and \002 escapes to color text which is *not*
        interpreted by readline, (for instance if you have a single function
        to color text and you want to use it to color both your sys.ps1 and
        output text), the \001 and \002 codes will get printed out using a
        representation (like a unicode 'box'[4]). So, one would have to
        workaround that in the text coloring function.

        [1] http://en.wikipedia.org/wiki/ANSI_escape_code#Colors
        [2] bugs.python.org/issue17337/ and
            http://stackoverflow.com/questions/9468435/look-how-to-fix-column-calculation-in-python-readline-if-use-color-prompt
        [3] http://gnometerminator.blogspot.sg/p/introduction.html
        [4] http://en.wikipedia.org/wiki/Control_character#Display

    Examples:
        TermColor.red('hello')
        TermColor.red('hello', is_escape_seq=True)

    """
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    LIGHT_BLUE = '\033[1;34m'
    PURPLE = '\033[35m'
    GREY = '\033[1;30m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @classmethod
    def to_colour(cls, string_to_colour, *, colour, is_escape_seq=False):
        colour = getattr(cls, colour.upper())
        end = cls.END
        if is_escape_seq:
            colour = f'\x01{colour}\x02'
            end = f'\x01{end}\x02'
        return colour + string_to_colour + end


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
        'precise': {
            'format': (
                '[%(asctime)s] [%(process)d:%(threadName)s] [%(levelname)s] '
                '[%(name)s] {%(pathname)s:%(lineno)d} %(message)s'
            )

        }
    },
    'handlers': {
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
    }
}
