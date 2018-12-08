from src.actions.abstract_base_action import AbstractBaseAction
from src.flashcard import Flashcard, FlashcardContainer


class GeneralCreateAction(AbstractBaseAction):

    @property
    def action_name(self):
        return 'create'

    async def launch(self):
        await super().launch()

        await self.mediator.print(f'Creating New Flashcard', bold=True)
        flashcard = await self._create_flashcard()

        duplicates: FlashcardContainer = await self.mediator.search_flashcard(
            flashcard.answer,
            flashcard.question
        )
        for duplicate in duplicates:
            await self.mediator.print(
                f'Possible duplicate',
                bold=True,
            )
            await self.mediator.print_flashcard(
                duplicate,
                bottom_margin=1,
                colour_func=self.mediator.format_red,
                exclude_fields=[
                    Flashcard.explanation,
                    Flashcard.examples
                ]
            )

        await self.mediator.print(
            'Creating flashcard',
            bottom_margin=1,
            bold=True,
        )
        await self.mediator.print_flashcard(
            flashcard,
            colour_func=self.mediator.format_yellow,
            bottom_margin=1,
            exclude_fields=[
                Flashcard.flashcard_id,
                Flashcard.review_timestamp,
                Flashcard.created
            ]
        )
        await self.mediator.print(
            f'Possible duplicates: {len(duplicates)}',
            bold=True
        )

        confirmed: bool = await self.mediator.input_confirmation(
            'Do you want to create?'
        )
        if confirmed:
            await self.mediator.save_flashcard(flashcard)
            await self.mediator.print(
                'Flashcard saved.',
                bottom_margin=1,
                bold=True
            )
            await self.mediator.print_flashcard(
                flashcard=flashcard,
                colour_func=self.mediator.format_yellow,
                bottom_margin=1,
                include_fields=[
                    Flashcard.flashcard_id,
                    Flashcard.question,
                    Flashcard.answer
                ]
            )
        else:
            await self.mediator.print(
                'Aborting creation',
                bottom_margin=1,
                red=True
            )

    async def _create_flashcard(self):
        question = await self.mediator.input_question()
        answer = await self.mediator.input_answer()
        source = await self.mediator.input_source()

        flashcard: Flashcard = Flashcard.create(
            user_id=self.mediator.get_user_id(),
            question=question,
            answer=answer,
            source=source
        )
        return flashcard

