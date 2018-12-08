from src.flashcard import FlashcardContainer
from src.actions.abstract_base_action import AbstractBaseAction


class GeneralSearchAction(AbstractBaseAction):

    @property
    def action_name(self):
        return 'search'

    async def launch(self):
        await super().launch()

        while True:
            await self.launch_search()
            confirmed: bool = await self.mediator.input_confirmation(
                'Do you want to continue search?'
            )
            if not confirmed:
                break

    async def launch_search(self):
        search_query = await self.mediator.input('Search')

        flashcard_container: FlashcardContainer = (
            await self.mediator.search_flashcard(search_query)
        )

        await self.mediator.print(
            f'Found flashcards: {len(flashcard_container)}',
            bold=True,
            bottom_margin=1
        )

        for flashcard in flashcard_container:
            await self.mediator.print_flashcard(
                flashcard,
                colour_func=self.mediator.format_purple,
                bottom_margin=1
            )

        return flashcard_container
