from src.actions.abstract_base_action import AbstractBaseAction
from src.flashcard import Flashcard, FlashcardContainer


class GeneralAlterAction(AbstractBaseAction):

    @property
    def action_name(self):
        return 'alter'

    async def launch(self):
        await super().launch()

        while True:
            flashcard_container: FlashcardContainer = (
                await self.mediator.launch_search()
            )

            action = await self.mediator.input_action(
                action_answers=tuple(
                    flashcard_container.get_ids() + ['c', 'q']
                ),
                action_msgs=[
                    f'Please, enter flashcard '
                    f'{self.mediator.format_light_blue("id")} '
                    f'you want to {self.mediator.format_light_blue("alter")}.',
                    f'If you want to continue, please enter '
                    f'{self.mediator.format_light_blue("c")}',
                    f'If you want to exit, please enter '
                    f'{self.mediator.format_red("q")}',
                ]
            )

            # Continue to search a flashcard in order to alter it.
            if action == 'c':
                continue

            # Quit alter action.
            if action == 'q':
                break

            flashcard: Flashcard = flashcard_container.get(flashcard_id=action)
            await self.mediator.print(
                f'Altering Flashcard[{flashcard.id}]',
                bold=True
            )
            await self._alter_flashcard(flashcard)

            await self.mediator.print(
                'Altered flashcard',
                bottom_margin=1,
                bold=True
            )
            await self.mediator.print_flashcard(
                flashcard,
                colour_func=self.mediator.format_light_blue,
                bottom_margin=1
            )

            confirmed: bool = await self.mediator.input_confirmation(
                'Do you want to alter?'
            )
            if confirmed:
                await self.mediator.update_flashcard(flashcard)
                await self.mediator.print(
                    'Flashcard updated.',
                    bottom_margin=1,
                    bold=True
                )
                await self.mediator.print_flashcard(
                    flashcard=flashcard,
                    colour_func=self.mediator.format_light_blue,
                    bottom_margin=1,
                    include_fields=[
                        Flashcard.flashcard_id,
                        Flashcard.question,
                        Flashcard.answer
                    ]
                )
            else:
                await self.mediator.print(
                    'Aborting altering',
                    bottom_margin=1,
                    red=True
                )

            break

    async def _alter_flashcard(self, flashcard: Flashcard):
        question = await self.mediator.input_question(
            pre_fill=flashcard.question
        )
        answer = await self.mediator.input_answer(
            pre_fill=flashcard.answer
        )
        source = await self.mediator.input_source(
            pre_fill=flashcard.source
        )

        flashcard.alter(
            question=question,
            answer=answer,
            source=source
        )
