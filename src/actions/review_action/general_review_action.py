import enum
import logging

from datetime import datetime

from src.utils import datetime_now, normalize_value
from src.actions.abstract_base_action import AbstractBaseAction
from src.flashcard import FlashcardContainer, Flashcard
from src.flashcard.flashcard_scheduler import FlashcardScheduler

logger = logging.getLogger(__name__)


class GeneralReviewAction(AbstractBaseAction):

    @property
    def action_name(self):
        return 'review'

    async def launch(self):
        await super().launch()

        flashcard_container: FlashcardContainer = (
            await self.mediator.get_ready_flashcards()
        )
        review_stat = ReviewStat(len(flashcard_container))
        review_stat.start()

        try:
            for ind, flashcard in enumerate(flashcard_container, start=1):
                can_continue = await self.process_flashcard(
                    ind, flashcard, review_stat
                )
                if not can_continue:
                    break

        finally:
            review_stat.finish()
            await self.mediator.print(
                'Game is over!',
                bottom_margin=1
            )
            await self.mediator.print(
                f'Playing time: {review_stat.playing_time}',

                f'{"Total".ljust(12)}: {str(review_stat.total).rjust(6)}',

                f'{"Reviewed".ljust(12)}: '
                f'{str(review_stat.reviewed).rjust(6)}',

                f'{"Right".ljust(12)}: '
                f'{str(review_stat.right).rjust(6)} '
                f'({review_stat.right_percent}%)',

                f'{"Wrong".ljust(12)}: '
                f'{str(review_stat.wrong).rjust(6)} '
                f'({review_stat.wrong_percent}%)',
                bottom_margin=1
            )

    async def process_flashcard(self, counter, flashcard: Flashcard, review_stat):
        await self.mediator.print(
            f'Flashcard[{flashcard.id}] #{counter} / #{review_stat.total}',
            bold=True
        )
        await self.make_review(flashcard, review_stat)

        confirmed: bool = await self.mediator.input_confirmation(
            'Do you want to continue?'
        )
        if not confirmed:
            return False
        return True

    async def make_review(self, flashcard: Flashcard, review_stat):
        previous_review_timestamp = await self.mediator.get_prev_review_timestamp(
            flashcard=flashcard
        )
        current_review_timestamp = datetime_now()

        await self.mediator.print(
            f'{self.mediator.format_grey("Question")}: '
            f'{flashcard.question}'
        )
        entered_answer = await self.mediator.input_answer()

        entered_answer = normalize_value(
            entered_answer, remove_trailing='.', to_lower=True
        )
        answer_side = normalize_value(
            flashcard.answer, remove_trailing='.', to_lower=True
        )

        edit_dist, entered_ans_alignment, ans_side_alignment = (
            self.compute_edit_distance(entered_answer, answer_side)
        )

        if edit_dist == 0:
            flashcard.review_timestamp = FlashcardScheduler.to_next(
                flashcard_answer=flashcard.answer,
                previous_review_timestamp=previous_review_timestamp
            )
            review_stat.inc_right()
            colour_func = self.mediator.format_green
            current_result = 'success'
        else:
            flashcard.review_timestamp = FlashcardScheduler.to_init(
                flashcard_answer=flashcard.answer
            )
            review_stat.inc_wrong()
            colour_func = self.mediator.format_red
            current_result = 'failure'

            await self.mediator.print(entered_ans_alignment)
            await self.mediator.print(ans_side_alignment, bottom_margin=1)

        flashcard.review_version += 1

        await self.mediator.print_flashcard(
            flashcard,
            colour_func=colour_func,
            exclude_fields=[
                Flashcard.flashcard_id,
                Flashcard.question
            ],
            bottom_margin=1
        )

        await self.mediator.update_flashcard_review_state(
            flashcard_id=flashcard.flashcard_id,
            current_review_timestamp=current_review_timestamp,
            current_result=current_result,
            next_review_timestamp=flashcard.review_timestamp,
            next_review_version=flashcard.review_version,
        )
        review_stat.inc_reviewed()

    def compute_edit_distance(self, first_str, second_str):
        """
        Given two strings, finds the minimum number of elementary operations,
        insertions, deletions, or substitutions of symbols that transform
        one string into another. Edit distance is a way of quantifying how
        dissimilar two strings are to one another by counting the minimum
        number of operations required to transform one string into the other.

        Returns the edit distance with an alignment of two strings.
        """
        distances = []
        for f_prefix in range(len(first_str) + 1):
            distances.append([None for _ in range(len(second_str) + 1)])

        for f_prefix in range(len(first_str) + 1):
            for s_prefix in range(len(second_str) + 1):

                if f_prefix == 0 and s_prefix == 0:
                    distances[f_prefix][s_prefix] = {
                        'dist': 0,
                        'backtrack_f_prefix': None,
                        'backtrack_s_prefix': None,
                        'operation': None,
                        'first_str_char': '',
                        'second_str_char': '',
                    }
                    continue

                if f_prefix == 0:
                    distances[f_prefix][s_prefix] = {
                        'dist': s_prefix,
                        'backtrack_f_prefix': f_prefix,
                        'backtrack_s_prefix': s_prefix - 1,
                        'operation': EditDistType.INSERTION,
                        'first_str_char': '-',
                        'second_str_char': second_str[s_prefix - 1],
                    }
                    continue

                if s_prefix == 0:
                    distances[f_prefix][s_prefix] = {
                        'dist': f_prefix,
                        'backtrack_f_prefix': f_prefix - 1,
                        'backtrack_s_prefix': s_prefix,
                        'operation': EditDistType.DELETION,
                        'first_str_char': first_str[f_prefix - 1],
                        'second_str_char': '-',
                    }
                    continue

                if first_str[f_prefix - 1] == second_str[s_prefix - 1]:
                    dist_1 = {
                        'dist': distances[f_prefix - 1][s_prefix - 1]['dist'],
                        'backtrack_f_prefix': f_prefix - 1,
                        'backtrack_s_prefix': s_prefix - 1,
                        'operation': EditDistType.MATCH,
                        'first_str_char': first_str[f_prefix - 1],
                        'second_str_char': second_str[s_prefix - 1],
                    }
                else:
                    dist_1 = {
                        'dist': distances[f_prefix - 1][s_prefix - 1]['dist'] + 1,
                        'backtrack_f_prefix': f_prefix - 1,
                        'backtrack_s_prefix': s_prefix - 1,
                        'operation': EditDistType.SUBSTITUTION,
                        'first_str_char': first_str[f_prefix - 1],
                        'second_str_char': second_str[s_prefix - 1],
                    }

                dist_2 = {
                    'dist': distances[f_prefix][s_prefix - 1]['dist'] + 1,
                    'backtrack_f_prefix': f_prefix,
                    'backtrack_s_prefix': s_prefix - 1,
                    'operation': EditDistType.INSERTION,
                    'first_str_char': '-',
                    'second_str_char': second_str[s_prefix - 1],
                }

                dist_3 = {
                    'dist': distances[f_prefix - 1][s_prefix]['dist'] + 1,
                    'backtrack_f_prefix': f_prefix - 1,
                    'backtrack_s_prefix': s_prefix,
                    'operation': EditDistType.DELETION,
                    'first_str_char': first_str[f_prefix - 1],
                    'second_str_char': '-',
                }

                distances[f_prefix][s_prefix] = min(
                    dist_1, dist_2, dist_3,
                    key=lambda d: d['dist']
                )

        _edit_distance = distances[f_prefix][s_prefix]['dist']

        first_str_alignment = ''
        second_str_alignment = ''
        last_row = f_prefix
        last_col = s_prefix

        while True:
            d = distances[last_row][last_col]
            if d['backtrack_f_prefix'] is None and d['backtrack_s_prefix'] is None:
                break

            if d['operation'] == EditDistType.MATCH:
                _f_char_align = self.mediator.format_green(d['first_str_char'])
                _s_char_align = self.mediator.format_green(d['second_str_char'])
            else:
                _f_char_align = self.mediator.format_red(d['first_str_char'])
                _s_char_align = self.mediator.format_red(d['second_str_char'])

            first_str_alignment = _f_char_align + first_str_alignment
            second_str_alignment = _s_char_align + second_str_alignment

            last_row = d['backtrack_f_prefix']
            last_col = d['backtrack_s_prefix']

        return _edit_distance, first_str_alignment, second_str_alignment


class ReviewStat:

    def __init__(self, total_flashcard: int):
        self.start_time = None
        self.end_time = None
        self.total = total_flashcard
        self.reviewed = 0
        self.right = 0
        self.wrong = 0

    @property
    def right_percent(self):
        if self.reviewed:
            return  round((self.right * 100) / self.reviewed)
        return 0

    @property
    def wrong_percent(self):
        if self.reviewed:
            return  round((self.wrong * 100) / self.reviewed)
        return 0

    @property
    def playing_time(self):
        return self.end_time - self.start_time

    def start(self):
        self.start_time = datetime.now()

    def finish(self):
        self.end_time = datetime.now()

    def inc_reviewed(self):
        self.reviewed += 1

    def inc_right(self):
        self.right += 1

    def inc_wrong(self):
        self.wrong += 1


class EditDistType(enum.Enum):
    MATCH = 'match'
    DELETION = 'deletion'
    INSERTION = 'insertion'
    SUBSTITUTION = 'substitution'
