import math

from datetime import timedelta

from src.utils import datetime_now


class FlashcardScheduler:

    @staticmethod
    def to_init(flashcard_answer):
        initial_timedelta_sec = 24 * 60 * 60
        delta_sec = initial_timedelta_sec / math.log(len(flashcard_answer))
        review_timestamp = datetime_now() + timedelta(
            seconds=initial_timedelta_sec + delta_sec
        )
        return review_timestamp

    @staticmethod
    def to_next(flashcard_answer, previous_review_timestamp):
        elapsed_timedelta = datetime_now() - previous_review_timestamp
        elapsed_seconds = elapsed_timedelta.total_seconds()
        delta_sec = elapsed_seconds / math.log(len(flashcard_answer))
        review_timestamp = datetime_now() + timedelta(
            seconds=elapsed_seconds + delta_sec
        )
        return review_timestamp

