import logging

from datetime import datetime

from src.utils import normalize_value
from src.flashcard.flashcard import Flashcard
from src.flashcard.flashcard_scheduler import FlashcardScheduler


logger = logging.getLogger(__name__)


class FlashcardReview:

    def __init__(
            self,
            flashcard: Flashcard,
            previous_review_timestamp: datetime
    ):
        self.flashcard = flashcard
        self.previous_review_timestamp = previous_review_timestamp
        self.is_success = None

    def make(self, entered_answer):
        entered_answer = normalize_value(
            entered_answer, remove_trailing='.', to_lower=True
        )
        flashcard_side_answer = normalize_value(
            self.flashcard.answer, remove_trailing='.', to_lower=True
        )
 
        if entered_answer == flashcard_side_answer:
            self.is_success = True
            self.flashcard.review_timestamp = FlashcardScheduler.to_next(
                flashcard_answer=self.flashcard.answer,
                previous_review_timestamp=self.previous_review_timestamp
            )
        else:
            self.is_success = False
            self.flashcard.review_timestamp = FlashcardScheduler.to_init(
                flashcard_answer=self.flashcard.answer
            )
