import logging

from datetime import datetime

from src.utils import normalize_value
from src.flashcard.flashcard_state import FlashcardState


logger = logging.getLogger(__name__)


class Field:

    def __init__(self, attr_name, print_name):
        self.attr_name = attr_name
        self.print_name = print_name

    @property
    def name(self):
        return self.attr_name

    def __get__(self, instance, owner):
        if instance:
            return instance.__dict__[self.attr_name]
        return self

    def __set__(self, instance, value):
        instance.__dict__[self.attr_name] = value


class FlashcardType(Field):
    def __init__(self, attr_name='flashcard_type', print_name='Type'):
        super().__init__(attr_name=attr_name, print_name=print_name)

    def __set__(self, instance, value):
        if not isinstance(value, str):
            err_msg = f'{self.attr_name}: {value!r} must be string.'
            raise TypeError(err_msg)

        value = normalize_value(value, to_lower=True)
        super().__set__(instance, value)


class UserId(Field):

    def __init__(self, attr_name='user_id', print_name='User id'):
        super().__init__(attr_name=attr_name, print_name=print_name)

    def __set__(self, instance, value):
        if not isinstance(value, int):
            err_msg = f'{self.attr_name}: {value!r} must be integer.'
            raise TypeError(err_msg)
        super().__set__(instance, value)


class FlashcardId(Field):
    def __init__(self, attr_name='flashcard_id', print_name='Flashcard ID'):
        super().__init__(attr_name=attr_name, print_name=print_name)

    def __set__(self, instance, value):
        if not isinstance(value, (int, type(None))):
            err_msg = f'{self.attr_name}: {value!r} must be integer or None.'
            raise TypeError(err_msg)
        super().__set__(instance, value)


class Question(Field):
    def __init__(self, attr_name='question', print_name='Question'):
        super().__init__(attr_name=attr_name, print_name=print_name)

    def __set__(self, instance, value):
        if not isinstance(value, str):
            err_msg = f'{self.attr_name}: {value!r} must be string.'
            raise TypeError(err_msg)

        value = normalize_value(value)
        super().__set__(instance, value)


class Answer(Field):
    def __init__(self, attr_name='answer', print_name='Answer'):
        super().__init__(attr_name=attr_name, print_name=print_name)

    def __set__(self, instance, value):
        if not isinstance(value, str):
            err_msg = f'{self.attr_name}: {value!r} must be string.'
            raise TypeError(err_msg)

        value = normalize_value(value)
        super().__set__(instance, value)


class PhoneticTranscription(Field):
    def __init__(
        self, attr_name='phonetic_transcription',
        print_name='Phonetic transcription'
    ):
        super().__init__(attr_name=attr_name, print_name=print_name)

    def __set__(self, instance, value):
        if not isinstance(value, (str, type(None))):
            err_msg = f'{self.attr_name}: {value!r} must be string or None.'
            raise TypeError(err_msg)

        if value is not None:
            value = normalize_value(value)

        super().__set__(instance, value)


class Source(Field):
    def __init__(self, attr_name='source', print_name='Source'):
        super().__init__(attr_name=attr_name, print_name=print_name)

    def __set__(self, instance, value):
        if not isinstance(value, (str, type(None))):
            err_msg = f'{self.attr_name}: {value!r} must be string or None.'
            raise TypeError(err_msg)

        if value is not None:
            value = normalize_value(value)

        super().__set__(instance, value)


class Explanation(Field):
    def __init__(self, attr_name='explanation', print_name='Explanation'):
        super().__init__(attr_name=attr_name, print_name=print_name)

    def __set__(self, instance, value):
        if not isinstance(value, (str, type(None))):
            err_msg = f'{self.attr_name}: {value!r} must be string or None.'
            raise TypeError(err_msg)

        if value is not None:
            value = normalize_value(value)

        super().__set__(instance, value)


class Examples(Field):
    def __init__(self, attr_name='examples', print_name='Examples'):
        super().__init__(attr_name=attr_name, print_name=print_name)

    def __set__(self, instance, value):
        if not isinstance(value, (list, type(None))):
            err_msg = f'{self.attr_name}: {value!r} must be list or None.'
            raise TypeError(err_msg)

        if value is not None:
            for i in range(len(value)):
                value[i] = normalize_value(value[i])

        super().__set__(instance, value)


class Created(Field):
    def __init__(self, attr_name='created', print_name='Created date'):
        super().__init__(attr_name=attr_name, print_name=print_name)

    def __set__(self, instance, value):
        if not isinstance(value, datetime):
            err_msg = f'{self.attr_name}: {value!r} must be datetime.'
            raise TypeError(err_msg)

        super().__set__(instance, value)


class ReviewTimestamp(Field):
    def __init__(self, attr_name='review_timestamp', print_name='Review date'):
        super().__init__(attr_name=attr_name, print_name=print_name)

    def __set__(self, instance, value):
        if not isinstance(value, datetime):
            err_msg = f'{self.attr_name}: {value!r} must be datetime.'
            raise TypeError(err_msg)

        super().__set__(instance, value)


class State(Field):
    def __init__(self, attr_name='state', print_name='State'):
        super().__init__(attr_name=attr_name, print_name=print_name)

    def __set__(self, instance, value):
        if not isinstance(value, FlashcardState):
            err_msg = (
                f'"{self.attr_name}" field must be FlashcardState type. '
                f'Type: {type(value)}, Value: {value!r}'
            )
            raise TypeError(err_msg)
        super().__set__(instance, value)
