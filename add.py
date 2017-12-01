from collections import deque
from datetime import timedelta

from db_session import DBSession
from flashcard import Flashcard
from config import ConfigAdapter
from utils import TermColor, datetime_utc_now
from base import AsyncIO


class AddFlashcard:

    def __init__(self, user_id, async_io: AsyncIO):
        self.user_id = user_id
        self.previous_sources = deque([None], maxlen=2)
        self.config = ConfigAdapter(filename='config.cfg')
        self.db_session = DBSession(self.config['database'].get('name'))
        self.async_io = async_io

    async def add(self):
        flashcard = Flashcard(user_id=self.user_id)
        await self.async_io.print(TermColor.bold('Add new flashcard:'))

        flashcard.side_a = await self.async_io.input('Side A')
        flashcard.side_b = await self.async_io.input('Side B')

        source = await self.async_io.input('Source')
        if source.strip() == '\p':
            source = self.previous_sources[0]
        else:
            self.previous_sources.appendleft(source)
        flashcard.source = source

        flashcard.phonetic_transcriptions = await self.async_io.input(
            'Phonetic transcriptions'
        )

        part_of_speech = await self.async_io.input('Part of speech')
        part_of_speech = part_of_speech.strip()

        explanation = await self.async_io.input('Explanation')
        if part_of_speech:
            flashcard.explanation = f'[{part_of_speech}] {explanation}'
        else:
            flashcard.explanation = f'{explanation}'

        flashcard.examples = await self.async_io.input('Examples')

        duplicates = self.db_session.get_flashcard_duplicates(flashcard)
        await self.show_duplicates(duplicates)

        flashcard.due = datetime_utc_now() + timedelta(days=2**flashcard.box)

        action_msgs=[
            TermColor.bold('Adding flashcard'),
            f'{TermColor.ligth_blue("Side A:")} {flashcard.side_a}',
            f'{TermColor.ligth_blue("Side B:")} {flashcard.side_b}',
            f'{TermColor.ligth_blue("Box:")} {flashcard.box}',
            f'{TermColor.ligth_blue("Due:")} {flashcard.due}',
            f'{TermColor.ligth_blue("Source:")} {flashcard.source}',
            f'{TermColor.ligth_blue("Phonetic transcriptions:")} '
            f'{flashcard.phonetic_transcriptions}',
            f'{TermColor.ligth_blue("Explanation:")} '
            f'{flashcard.explanation}',
            f'{TermColor.ligth_blue("Examples:")} {flashcard.examples}',
            f'',
        ]

        if duplicates:
            action_msgs.append(
                f'{TermColor.purple(f"Duplicates: {len(duplicates)}")}'
            )

        action_msgs.extend([
            f'Do you want to add '
            f'[{TermColor.green("y")}/{TermColor.red("n")}] ?',
        ])

        action = await self.async_io.input_action(
            action_answers=('y', 'n'), action_msgs=action_msgs
        )

        if action == 'y':
            self.db_session.add_flashcard(flashcard=flashcard)
            await self.async_io.print(TermColor.bold(f'Added: {flashcard}'))
        else:
            await self.async_io.print(TermColor.red('Aborting flashcard.'))

    async def show_duplicates(self, duplicates):
        if duplicates:
            await self.async_io.print(
                TermColor.bold(f'Duplicate flashcards: {len(duplicates)}')
            )
            for duplicate in duplicates:
                await self.async_io.print(
                    f'{TermColor.purple("Side A:")} {duplicate["side_a"]}',
                    f'{TermColor.purple("Side B:")} {duplicate["side_b"]}',
                    f'{TermColor.purple("Box:")} {duplicate["box"]}',
                    f'{TermColor.purple("Due:")} {duplicate["due"]}',
                    f'{TermColor.purple("User:")} {duplicate["user_id"]}',
                    f'{TermColor.purple("Source:")} {duplicate["source"]}',
                    f'{TermColor.purple("Created:")} {duplicate["created"]}'
                )
