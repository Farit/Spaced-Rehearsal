from datetime import datetime

from src.utils import normalize_value


class Field:

    def __init__(self):
        self.name = None

    def __get__(self, instance, owner):
        if instance:
            return instance.__dict__[self.name]
        return self

    def __set__(self, instance, value):
        instance.__dict__[self.name] = value


class FlashcardMetaclass(type):

    def __init__(cls, name, bases, dic):
        super().__init__(name, bases, dic)
        for attr_name, attr in dic.items():
            if isinstance(attr, Field):
                attr.name = attr_name


class Side(Field):
    def __set__(self, instance, value):
        if not isinstance(value, (str, type(None))):
            raise TypeError(f'{self.name}: {value!r} must be str or None')

        if value is not None:
            value = normalize_value(value)

        super().__set__(instance, value)


class SideA(Side):
    pass


class SideB(Side):
    pass


class Box(Field):
    def __set__(self, instance, value):
        if not isinstance(value, int):
            raise TypeError(f'{self.name}: {value!r} must be int')
        super().__set__(instance, value)


class Due(Field):
    def __set__(self, instance, value):
        if not isinstance(value, (datetime, type(None))):
            raise TypeError(f'{self.name}: {value!r} must be datetime or None')
        super().__set__(instance, value)


class Source(Field):

    def __init__(self):
        super().__init__()

    def __set__(self, instance, value):
        if not isinstance(value, (str, type(None))):
            raise TypeError(f'{self.name}: {value!r} must be str or None')

        value = value.strip() if value else value
        super().__set__(instance, value)


class PhoneticTranscriptions(Field):
    def __set__(self, instance, value):
        if not isinstance(value, (str, type(None))):
            raise TypeError(f'{self.name}: {value!r} must be str or None')
        super().__set__(instance, value)


class Explanation(Field):
    def __set__(self, instance, value):
        if not isinstance(value, (str, type(None))):
            raise TypeError(f'{self.name}: {value!r} must be str or None')
        super().__set__(instance, value)


class Examples(Field):
    def __set__(self, instance, value):
        if not isinstance(value, (str, type(None))):
            raise TypeError(f'{self.name}: {value!r} must be str or None')
        super().__set__(instance, value)


class Flashcard(metaclass=FlashcardMetaclass):
    side_a = SideA()
    side_b = SideB()
    box = Box()
    due = Due()
    source = Source()
    phonetic_transcriptions = PhoneticTranscriptions()
    explanation = Explanation()
    examples = Examples()

    def __init__(
        self, *, user_id, id=None, side_a=None, side_b=None, box=None,
        due=None, source=None, phonetic_transcriptions=None,
        explanation=None, examples=None, created=None
    ):
        self.id = id
        self.user_id = user_id
        self.side_a = side_a
        self.side_b = side_b
        self.box = 0 if box is None else box
        self.due = due
        self.source = source
        self.phonetic_transcriptions = phonetic_transcriptions
        self.explanation = explanation
        self.examples = examples
        self.created = created

    def __str__(self):
        return f'[{self.side_a}] / [{self.side_b}]'

    def __getitem__(self, item):
        return getattr(self, item)
