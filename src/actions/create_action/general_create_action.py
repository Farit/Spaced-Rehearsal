from src.actions.abstract_base_action import AbstractBaseAction
from src.flashcard import Flashcard, FlashcardContainer


class GeneralCreateAction(AbstractBaseAction):

    @property
    def action_name(self):
        return 'create'

    async def launch(self):
        await super().launch()

        await self.mediator.print(f'Creating New Flashcard', bold=True)
        data = await self._collect_data()

        if not data.get('answer') or not data.get('question'):
            await self.mediator.print(
                'Aborting creation. Either answer or question is empty.',
                bottom_margin=1,
                red=True
            )
            return

        flashcard: Flashcard = Flashcard.create(
            user_id=self.mediator.get_user_id(),
            flashcard_type=self.mediator.name(),
            question=data.get('question'),
            answer=data.get('answer'),
            source=data.get('source'),
            phonetic_transcription=data.get('phonetic_transcription'),
            explanation=data.get('explanation'),
            examples=data.get('examples')
        )

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

    async def _collect_data(self):
        data = {}
        data['question'] = await self.mediator.input_question()
        data['answer'] = await self.mediator.input_answer()
        data['source'] = await self.mediator.input_source()
        return data
