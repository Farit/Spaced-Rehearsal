from datetime import datetime

from src.utils import datetime_now
from src.actions.abstract_base_action import AbstractBaseAction
from src.flashcard import FlashcardContainer, Flashcard, FlashcardReview


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
            await self.mediator.print(len(flashcard_container))
            for ind, flashcard in enumerate(flashcard_container, start=1):
                await self.mediator.print(
                    f'Flashcard[{flashcard.id}] #{ind} / #{review_stat.total}',
                    bold=True
                )
                await self.make_review(flashcard, review_stat)

                confirmed: bool = await self.mediator.input_confirmation(
                    'Do you want to continue?'
                )
                if not confirmed:
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
                f'{"Reviewed".ljust(12)}: {str(review_stat.reviewed).rjust(6)}',
                f'{"Right".ljust(12)}: {str(review_stat.right).rjust(6)}',
                f'{"Wrong".ljust(12)}: {str(review_stat.wrong).rjust(6)}',
                bottom_margin=1
            )

    async def make_review(self, flashcard: Flashcard, review_stat):
        previous_review_timestamp = await self.mediator.get_prev_review_timestamp(
            flashcard=flashcard
        )
        current_review_timestamp = datetime_now()

        flashcard_review = FlashcardReview(
            flashcard=flashcard,
            previous_review_timestamp=previous_review_timestamp
        )

        await self.mediator.print(
            f'{self.mediator.format_grey("Question")}: '
            f'{flashcard.question}'
        )
        entered_answer = await self.mediator.input_answer()

        flashcard_review.make(entered_answer=entered_answer)
        if flashcard_review.is_success:
            review_stat.inc_right()
            colour_func = self.mediator.format_green
            current_result = 'success'
        else:
            review_stat.inc_wrong()
            colour_func = self.mediator.format_red
            current_result = 'failure'

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
        )
        review_stat.inc_reviewed()


class ReviewStat:

    def __init__(self, total_flashcard: int):
        self.start_time = None
        self.end_time = None
        self.total = total_flashcard
        self.reviewed = 0
        self.right = 0
        self.wrong = 0

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
