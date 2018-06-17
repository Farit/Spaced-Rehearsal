import logging
import textwrap
import re

from datetime import datetime
from typing import Optional, List

from src.utils import normalize_value, TermColor
from src.scheduler import FlashcardState


logger = logging.getLogger(__name__)


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


class OptionalStr(Field):
    def __set__(self, instance, value):
        if not isinstance(value, (str, type(None))):
            raise TypeError(f'{self.name}: {value!r} must be str or None')

        if value is not None:
            value = normalize_value(value)

        super().__set__(instance, value)


class Integer(Field):
    def __set__(self, instance, value):
        if not isinstance(value, (int, type(None))):
            raise TypeError(f'{self.name}: {value!r} must be integer')
        super().__set__(instance, value)


class OptionalInt(Field):
    def __set__(self, instance, value):
        if not isinstance(value, (int, type(None))):
            raise TypeError(f'{self.name}: {value!r} must be int or None')
        super().__set__(instance, value)


class OptionalDateTime(Field):
    def __set__(self, instance, value):
        if not isinstance(value, (datetime, type(None))):
            raise TypeError(f'{self.name}: {value!r} must be datetime or None')
        super().__set__(instance, value)


class OptionalFlashcardState(Field):
    def __set__(self, instance, value):
        if not isinstance(value, (FlashcardState, type(None))):
            raise TypeError(f'{self.name}: {value!r} must be state or None')
        super().__set__(instance, value)


class Flashcard(metaclass=FlashcardMetaclass):
    user_id = Integer()
    flashcard_id = OptionalInt()
    side_question = OptionalStr()
    side_answer = OptionalStr()
    phonetic_transcriptions = OptionalStr()
    source = OptionalStr()
    explanation = OptionalStr()
    examples = OptionalStr()
    created = OptionalDateTime()
    review_timestamp = OptionalDateTime()
    state = OptionalFlashcardState()

    def __init__(
        self, *,
        user_id: int,
        flashcard_id: Optional[int]=None,
        side_question: Optional[str]=None,
        side_answer: Optional[str]=None,
        phonetic_transcriptions: Optional[str]=None,
        source: Optional[str]=None,
        explanation: Optional[str]=None,
        examples: Optional[str]=None,
        created: Optional[datetime]=None,
        review_timestamp: Optional[datetime]=None,
        state: Optional[FlashcardState]=None
    ):
        self.flashcard_id = flashcard_id
        self.user_id = user_id
        self.side_question = side_question
        self.side_answer = side_answer
        self.review_timestamp = review_timestamp
        self.source = source
        self.phonetic_transcriptions = phonetic_transcriptions
        self.explanation = explanation
        self.examples = examples
        self.created = created

        self.set_state(state)

    def get_examples(self):
        examples = (self.examples or "").strip()
        return examples.split(';') if examples else []

    def set_examples(self, examples: List[str]):
        self.examples = ';'.join(examples)

    def set_state(self, state):
        if state is None:
            self.state = None

        elif isinstance(state, FlashcardState):
            self.state = state

        elif isinstance(state, str):
            match = re.match(
                r'''
                    ^(?P<state>.+);
                    (?P<answer_difficulty>.+);
                    (?P<delay>.+);
                    (?P<mem_strength>.+)$
                ''',
                state,
                flags=re.VERBOSE
            )
            if match:
                state = match.group('state')
                answer_difficulty = float(match.group('answer_difficulty'))
                delay = int(match.group('delay'))
                mem_strength = match.group('mem_strength')
                mem_strength = (
                    int(mem_strength) if mem_strength != 'None' else None
                )
                self.state = FlashcardState(
                    state=state, answer_difficulty=answer_difficulty,
                    delay=delay, mem_strength=mem_strength
                )
            else:
                raise ValueError(
                    f'State {state!r} has inappropriate format, must be '
                    f'"state;answer_difficulty;delay;mem_strength"'
                )

        else:
            raise TypeError(f'Value {state!r} must be state or str')

    def pformat(self, term_color, exclude_fields=None, include_fields=None):
        """
        :param term_color: TermColor colour, e.g TermColor.grey or
        TermColor.purple
        :param exclude_fields: Which flashcard fields must be excluded.
        :param include_fields: Which flashcard fields must be included.
        """
        if exclude_fields is not None and include_fields is not None:
            raise Exception(
                'You can not specify both exclude_fields and include_fields'
            )

        available_fields_to_format = [
            'side_question',
            'side_answer',
            'review_timestamp',
            'source',
            'phonetic_transcriptions',
            'explanation',
            'examples',
            'created'
        ]

        output = []

        if exclude_fields is not None:
            fields_to_format = [
                f for f in available_fields_to_format if f not in exclude_fields
            ]
        elif include_fields is not None:
            fields_to_format = include_fields
        else:
            fields_to_format = available_fields_to_format

        for field in fields_to_format:
            output.extend(self._pformat_field(term_color, field))

        return output

    def _pformat_field(self, term_color, field):
        """
        :param term_color: TermColor colour, e.g TermColor.grey or
        TermColor.purple
        :param field: Which flashcard field must be formatted.
        """
        if field == 'side_question':
            return [f'{term_color("Question: ")}{self.side_question}']

        if field == 'side_answer':
            return [f'{term_color("Answer: ")}{self.side_answer}']

        if field == 'review_timestamp':
            return [f'{term_color("Review date: ")}{self.review_timestamp}']

        if field == 'source':
            source = (self.source or "").strip()
            return [f'{term_color("Source: ")}{source}'] if source else []

        if field == 'phonetic_transcriptions':
            spelling = (self.phonetic_transcriptions or "").strip()
            if spelling:
                res = f'{term_color("Phonetic transcriptions: ")}{spelling}'

                # Order of the substitution matters.
                spelling_highlight = re.sub(
                    r'(?<=[^\s])/\s?', f'/{TermColor.END} ', spelling
                )
                if spelling_highlight != spelling:
                    spelling_highlight = re.sub(
                        r'\s/', f' {TermColor.BOLD}/', spelling_highlight
                    )
                    res = (
                        f'{term_color("Phonetic transcriptions: ")}'
                        f'{spelling_highlight}'
                    )

                return [res]
            return []

        if field == 'explanation':
            explanation = (self.explanation or "").strip()
            if explanation:
                return [f'{term_color("Explanation: ")}{explanation}']
            return []

        if field == 'examples':
            output = []
            examples = self.get_examples()
            if examples:
                output = [f'{term_color("Examples: ")}']
                examples.sort(reverse=True)
                for ind, example in enumerate(examples, start=1):
                    example = example.strip()
                    if example:
                        formatted_example = f'{ind}: {example}'
                        output.append(textwrap.indent(formatted_example, ' '*4))
            return output

        if field == 'created':
            return [f'{term_color("Created date: ")}{self.created}']

    def __str__(self):
        return f'[{self.side_question}] / [{self.side_answer}]'

    def __getitem__(self, item):
        return getattr(self, item)

    def __iter__(self):
        return iter([
            ('flashcard_id', self.flashcard_id),
            ('user_id', self.user_id),
            ('side_question', self.side_question),
            ('side_answer', self.side_answer),
            ('review_timestamp', self.review_timestamp),
            ('source', self.source),
            ('phonetic_transcriptions', self.phonetic_transcriptions),
            ('explanation', self.explanation),
            ('examples', self.examples),
            ('created', self.created),
            ('state', self.state),
        ])

