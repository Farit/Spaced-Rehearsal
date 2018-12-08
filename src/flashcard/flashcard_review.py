import logging

from src.utils import normalize_value
from src.flashcard.flashcard import Flashcard
from src.flashcard.flashcard_scheduler import FlashcardScheduler


logger = logging.getLogger(__name__)


class FlashcardReview:

    def __init__(self, flashcard: Flashcard):
        self.flashcard = flashcard
        self.is_success = None
        self.scheduler: FlashcardScheduler = FlashcardScheduler(
            flashcard_answer_side=flashcard.answer,
            current_state=flashcard.state,
            current_review_timestamp=flashcard.review_timestamp
        )

    def make(self, entered_answer):
        entered_answer = normalize_value(
            entered_answer, remove_trailing='.', to_lower=True
        )
        flashcard_side_answer = normalize_value(
            self.flashcard.answer, remove_trailing='.', to_lower=True
        )
 
        if entered_answer == flashcard_side_answer:
            self.is_success = True
            self.scheduler.to_success()
        else:
            self.is_success = False
            self.scheduler.to_failure()

        self.flashcard.state = self.scheduler.next_state
        self.flashcard.review_timestamp = self.scheduler.next_review_timestamp
