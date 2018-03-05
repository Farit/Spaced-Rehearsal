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

    async def __call__(self):
        search_query = await self.async_io.input('Search')
        flashcards = self.db_session.search(search_query, user_id=self.user_id)

        if flashcards:
            await self.show_flashcards(flashcards)
        else:
            action_msgs =[
                f'{TermColor.red(f"Nothing is found!")}',
                f'Do you want to continue search '
                f'[{TermColor.green("y")}/{TermColor.red("n")}] ?',
            ]

            action = await self.async_io.input_action(
                action_answers=('y', 'n'), action_msgs=action_msgs
            )

            if action == 'y':
                flashcards = await self.__call__()

        return flashcards

    async def show_flashcards(self, flashcards: List[Flashcard]):
        if flashcards:
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
