import re
import time
import datetime
import string


class TermColor:
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
    """
    RED = '\x01\033[31m\x02'
    GREEN = '\x01\033[32m\x02'
    YELLOW = '\x01\033[33m\x02'
    BLUE = '\x01\033[34m\x02'
    LIGHT_BLUE = '\x01\033[1;34m\x02'
    PURPLE = '\x01\033[35m\x02'
    GREY = '\x01\033[1;30m\x02'
    END = '\x01\033[0m\x02'
    BOLD = '\x01\033[1m\x02'
    UNDERLINE = '\x01\033[4m\x02'

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
    def light_blue(cls, string_to_color):
        return cls.coloralize(cls.LIGHT_BLUE, string_to_color)

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

