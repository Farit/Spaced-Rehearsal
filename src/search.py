from typing import List

from src.db_session import DBSession
from src.config import ConfigAdapter
from src.utils import TermColor
from src.base import AsyncIO
from src.flashcard import Flashcard


class Search:
    def __init__(self, user_id: int, async_io: AsyncIO):
        self.user_id = user_id
        self.config = ConfigAdapter(filename='config.cfg')
        self.db_session = DBSession(self.config['database'].get('name'))
        self.async_io = async_io

    async def launch_search(self):
        while True:
            flashcards = await self.conduct_search()

            # Do continue search or exit?
            action_msgs = [
                f'Do you want to continue search '
                f'[{TermColor.green("y")}/{TermColor.red("n")}] ?',
            ]
            action = await self.async_io.input_action(
                action_answers=('y', 'n'), action_msgs=action_msgs
            )

            if action == 'n':
                break

    async def conduct_search(self):
        # Ask for the phrase
        search_query = await self.async_io.input('Search')

        # Seek flashcards by phrase
        flashcards = self.db_session.search(
            search_query,
            user_id=self.user_id
        )

        # Display search result.
        if flashcards:
            await self._display_flashcards(flashcards)
        else:
            await self.async_io.print(TermColor.red(f'Nothing is found!'))

        return flashcards

    async def _display_flashcards(self, flashcards: List[Flashcard]):
        await self.async_io.print(
            TermColor.bold(
                f'Found flashcards: {len(flashcards)}'
            )
        )
        for flashcard in flashcards:
            output = [
                f'{TermColor.purple("Flashcard id:")} '
                f'{flashcard["flashcard_id"]}',
            ]
            output.extend(
                flashcard.pformat(
                    term_color=TermColor.purple
                )
            )
            await self.async_io.print_formatted_output(output)
