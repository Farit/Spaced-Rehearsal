from datetime import datetime

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
        flashcard_review = FlashcardReview(flashcard)

        await self.mediator.print(
            f'{self.mediator.format_grey("Question")}: '
            f'{flashcard.question}'
        )
        entered_answer = await self.mediator.input_answer()

        flashcard_review.make(entered_answer=entered_answer)
        if flashcard_review.is_success:
            review_stat.inc_right()
            colour_func = self.mediator.format_green
        else:
            review_stat.inc_wrong()
            colour_func = self.mediator.format_red

        await self.mediator.print_flashcard(
            flashcard,
            colour_func=colour_func,
            exclude_fields=[
                Flashcard.flashcard_id,
                Flashcard.question
            ],
            bottom_margin=1
        )

        await self.mediator.update_flashcard_state(flashcard)
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
