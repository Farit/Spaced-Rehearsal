import textwrap
import re

from datetime import datetime
from typing import Optional, List

from src.utils import normalize_value
from src.scheduler import FlashcardState


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

    def pformat(self, term_color, exclude_fields=None):
        """
        :param term_color: TermColor colour, e.g TermColor.grey or
        TermColor.purple
        :param exclude_fields: Which flashcard's fields must be excluded.
        """
        exclude_fields = exclude_fields or []
        output = []

        if 'side_question' not in exclude_fields:
            output.append(
                f'{term_color("Question: ")}{self.side_question}'
            )

        if 'side_answer' not in exclude_fields:
            output.append(
                f'{term_color("Answer: ")}{self.side_answer}'
            )

        if 'review_timestamp' not in exclude_fields:
            output.append(
                f'{term_color("Review date: ")}'
                f'{self.review_timestamp}',
            )

        if 'source' not in exclude_fields:
            source = (self.source or "").strip()
            if source:
                output.append(
                    f'{term_color("Source: ")}{source}'
                )

        if 'phonetic_transcriptions' not in exclude_fields:
            phonetic_trans = (self.phonetic_transcriptions or "").strip()
            if phonetic_trans:
                output.append(
                    f'{term_color("Phonetic transcriptions: ")}{phonetic_trans}'
                )

        if 'explanation' not in exclude_fields:
            explanation = (self.explanation or "").strip()
            if explanation:
                output.append(
                    f'{term_color("Explanation: ")}{explanation}'
                )

        if 'examples' not in exclude_fields:
            examples = self.get_examples()
            if examples:
                output.append(f'{term_color("Examples: ")}')
                examples.sort(reverse=True)
                for ind, example in enumerate(examples, start=1):
                    example = example.strip()
                    if example:
                        formatted_example = f'{ind}: {example}'
                        output.append(textwrap.indent(formatted_example, ' '*4))

        if 'created' not in exclude_fields:
            output.append(
                f'{term_color("Created date: ")}'
                f'{self.created}',
            )

        return output

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

