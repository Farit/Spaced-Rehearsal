import logging
import textwrap

from datetime import datetime
from typing import Optional, List

from src.utils import datetime_now
from src.flashcard.flashcard_fields import (
    UserId, FlashcardId, Question, Answer, PhoneticTranscription, Source,
    Explanation, Examples, Created, ReviewTimestamp, State
)
from src.flashcard.flashcard_scheduler import FlashcardScheduler
from src.flashcard.flashcard_state import FlashcardState

logger = logging.getLogger(__name__)


class Flashcard:
    user_id = UserId()
    flashcard_id = FlashcardId()
    question = Question()
    answer = Answer()
    phonetic_transcription = PhoneticTranscription()
    source = Source()
    explanation = Explanation()
    examples = Examples()
    created = Created()
    review_timestamp = ReviewTimestamp()
    state = State()

    def __init__(
            self, *,
            user_id: int,
            question: str=None,
            answer: str=None,
            created: datetime,
            review_timestamp: datetime,
            state: FlashcardState,
            flashcard_id: Optional[int]=None,
            phonetic_transcription: Optional[str]=None,
            source: Optional[str]=None,
            explanation: Optional[str]=None,
            examples: Optional[list]=None,
    ):
        self.user_id = user_id
        self.question = question
        self.answer = answer
        self.created = created
        self.review_timestamp = review_timestamp
        self.state = state

        self.flashcard_id = flashcard_id
        self.phonetic_transcription = phonetic_transcription
        self.source = source
        self.explanation = explanation
        self.examples = examples

    @classmethod
    def create(
        cls, *, user_id: int, question: str, answer: str,
        phonetic_transcription: str=None, source: str=None,
        explanation: str=None, examples: List[str]=None
    ):
        scheduler = FlashcardScheduler(
            flashcard_answer_side=answer
        )
        scheduler.to_init()

        flashcard = cls(
            user_id=user_id,
            question=question,
            answer=answer,
            created=datetime_now(),
            state=scheduler.next_state,
            review_timestamp=scheduler.next_review_timestamp,
            flashcard_id=None,
            phonetic_transcription=phonetic_transcription,
            source=source,
            explanation=explanation,
            examples=examples
        )
        return flashcard

    def alter(
        self, *, question: str=None, answer: str=None,
        phonetic_transcription: str=None, source: str=None,
        explanation: str=None, examples: List[str]=None,
    ):
        if question is not None:
            self.question = question
        if answer is not None:
            self.answer = answer
        if phonetic_transcription is not None:
            self.phonetic_transcription = phonetic_transcription
        if source is not None:
            self.source = source
        if explanation is not None:
            self.explanation = explanation
        if examples is not None:
            self.examples = examples

    @property
    def id(self):
        return self.flashcard_id

    def print_format(self, fields=None):
        _format = []
        for field in self.printable_fields:
            if fields is not None and field not in fields:
                continue

            if field.attr_name == self.__class__.examples.attr_name:
                if self.examples:
                    data = [(self.__class__.examples.print_name, '')]
                    for ind, example in enumerate(self.examples, start=1):
                        _indent = textwrap.indent(f'{ind}', ' '*4)
                        data.append((_indent, example))
                    _format.extend(data)
                continue

            if getattr(self, field.attr_name):
                data = [(field.print_name, getattr(self, field.attr_name))]
                _format.extend(data)

        return _format

    def __str__(self):
        return f'{self.__class__}[{self.flashcard_id}]'

    def __getitem__(self, item):
        return getattr(self, item)

    @property
    def printable_fields(self):
        return [
            self.__class__.flashcard_id,
            self.__class__.question,
            self.__class__.answer,
            self.__class__.source,
            self.__class__.phonetic_transcription,
            self.__class__.explanation,
            self.__class__.examples,
            self.__class__.created,
            self.__class__.review_timestamp
        ]

    def __iter__(self):
        return iter([
            ('flashcard_id', self.flashcard_id),
            ('user_id', self.user_id),
            ('question', self.question),
            ('answer', self.answer),
            ('source', self.source),
            ('phonetic_transcription', self.phonetic_transcription),
            ('explanation', self.explanation),
            ('examples', self.examples),
            ('review_timestamp', self.review_timestamp),
            ('created', self.created),
            ('state', self.state),
        ])
