import math

from datetime import datetime, timedelta

from src.utils import datetime_now, convert_datetime_to_local, datetime_utc_now


class FlashcardState:
    def __init__(self, state, answer_difficulty, delay, mem_strength):
        if state not in ['init', 'success', 'failure']:
            raise Exception(f'Unknown state: {state}')

        self.state = state
        self.answer_difficulty = answer_difficulty
        self.delay = delay
        self.mem_strength = mem_strength

    def __repr__(self):
        return (
            f'<{self.state}  answer_difficulty: {self.answer_difficulty} '
            f'delay: {timedelta(hours=self.delay)} '
            f'mem_strength: {self.mem_strength}>'
        )


class FlashcardScheduler:

    def __init__(
            self, flashcard_answer_side: str,
            current_review_timestamp: datetime=None,
            current_state: FlashcardState=None
    ):
        self.flashcard_answer_side = flashcard_answer_side
        self.len_flashcard_answer_side = len(self.flashcard_answer_side)
        self.current_review_timestamp: datetime = current_review_timestamp
        self.current_state: FlashcardState = current_state
        self.next_review_timestamp: datetime = None
        self.next_state: FlashcardState = None

    def to_init(self):
        self.next_state = FlashcardState(
            'init',
            answer_difficulty=math.log(self.len_flashcard_answer_side),
            delay=24,
            mem_strength=None
        )
        self.next_review_timestamp = datetime_utc_now() + timedelta(
            hours=self.next_state.delay
        )

    def to_success(self):
        if self.current_state is None:
            raise Exception(f'Flashcard current state must be set.')

        if self.current_review_timestamp is None:
            raise Exception(f'Flashcard current review timestamp must be set.')

        now = datetime_now()
        current_review_timestamp = convert_datetime_to_local(
            self.current_review_timestamp
        )

        if now > current_review_timestamp:
            diff_timedelta = now - current_review_timestamp
            hours = int(diff_timedelta.total_seconds() / 3600)
        else:
            diff_timedelta = current_review_timestamp - now
            hours = -int(diff_timedelta.total_seconds() / 3600)

        current_delay = hours + self.current_state.delay

        if self.current_state.mem_strength is None:
            mem_strength = self.compute_mem_strength(
                answer_difficulty=self.current_state.answer_difficulty,
                delay=current_delay,
                probability=0.9
            )
        else:
            mem_strength = (
                    self.current_state.mem_strength + current_delay
            )

        next_delay = self.compute_delay(
            answer_difficulty=self.current_state.answer_difficulty,
            mem_strength=mem_strength,
            probability=0.8
        )

        self.next_state = FlashcardState(
            'success',
            answer_difficulty=self.current_state.answer_difficulty,
            delay=next_delay,
            mem_strength=mem_strength
        )
        self.next_review_timestamp = datetime_utc_now() + timedelta(
            hours=self.next_state.delay
        )

    def to_failure(self):
        self.next_state = FlashcardState(
            'failure',
            answer_difficulty=math.log(self.len_flashcard_answer_side),
            delay=24,
            mem_strength=None
        )
        self.next_review_timestamp = datetime_utc_now() + timedelta(
            hours=self.next_state.delay
        )

    @staticmethod
    def compute_mem_strength(answer_difficulty, delay, probability):
        numerator = answer_difficulty * delay
        denominator = math.log(1/probability)
        return int(numerator / denominator)

    @staticmethod
    def compute_delay(answer_difficulty, mem_strength, probability):
        numerator = mem_strength * math.log(1/probability)
        denominator = answer_difficulty
        return int(numerator / denominator)

