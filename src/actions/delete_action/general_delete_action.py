from src.actions.abstract_base_action import AbstractBaseAction
from src.flashcard import Flashcard, FlashcardContainer


class GeneralDeleteAction(AbstractBaseAction):

    @property
    def action_name(self):
        return 'delete'

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
                    f'{self.mediator.format_red("id")} '
                    f'you want to {self.mediator.format_red("delete")}.',
                    f'If you want to continue, please enter '
                    f'{self.mediator.format_red("c")}',
                    f'If you want to exit, please enter '
                    f'{self.mediator.format_red("q")}',
                ]
            )
            
            # Continue to search a flashcard in order to delete it.
            if action == 'c':
                continue

            # Quit delete action.
            if action == 'q':
                break

            # Delete chosen flashcard.
            flashcard: Flashcard = flashcard_container.get(flashcard_id=action)
            await self.mediator.print(
                'Deleting flashcard',
                bottom_margin=1,
                bold=True
            )
            await self.mediator.print_flashcard(
                flashcard,
                colour_func=self.mediator.format_red,
                bottom_margin=1
            )

            confirmed: bool = await self.mediator.input_confirmation(
                'Do you want to delete'
            )
            if confirmed:
                await self.mediator.delete_flashcard(flashcard)
                await self.mediator.print(
                    'Deleted flashcard',
                    bottom_margin=1,
                    bold=True
                )
                await self.mediator.print_flashcard(
                    flashcard=flashcard,
                    colour_func=self.mediator.format_red,
                    bottom_margin=1,
                    include_fields=[
                        Flashcard.flashcard_id,
                        Flashcard.question,
                        Flashcard.answer
                    ]
                )
            else:
                await self.mediator.print(
                    'Aborting deleting',
                    bottom_margin=1,
                    red=True
                )

            break
