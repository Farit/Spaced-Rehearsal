import re
import time
import datetime
import string


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
