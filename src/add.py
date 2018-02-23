from collections import deque
from typing import List

from src.db_session import DBSession
from src.flashcard import Flashcard
from src.config import ConfigAdapter
from src.utils import TermColor, datetime_utc_now, convert_datetime_to_local
from src.base import AsyncIO
from src.scheduler import FlashcardScheduler


class AddFlashcard:

    def __init__(self, user_id, async_io: AsyncIO):
        self.user_id = user_id
        self.previous_sources = deque([], maxlen=5)
        self.config = ConfigAdapter(filename='config.cfg')
        self.db_session = DBSession(self.config['database'].get('name'))
        self.async_io = async_io

    def popleft_previous_sources(self):
        if self.previous_sources:
            self.previous_sources.popleft()

    async def add(self):
        flashcard: Flashcard = Flashcard(user_id=self.user_id)
        await self.async_io.print(
            f'Pressing {TermColor.red("Ctrl+D")} terminates adding.',
            TermColor.bold('New flashcard:')
        )

        flashcard.side_question = await self.async_io.input('Question')
        flashcard.side_answer = await self.async_io.input('Answer')

        source = await self.async_io.input(
            'Source',
            pre_fill=self.previous_sources[0] if self.previous_sources else ''
        )
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

        examples = []
        example = await self.async_io.input('Example')
        while example:
            examples.append(example)
            example = await self.async_io.input('Example')
        flashcard.set_examples(examples)

        duplicates = self.db_session.get_flashcard_duplicates(flashcard)
        await self.show_duplicates(duplicates)

        if flashcard.side_answer:
            scheduler = FlashcardScheduler(
                flashcard_answer_side=flashcard.side_answer
            )
            scheduler.to_init()
            flashcard.state = scheduler.next_state
            flashcard.review_timestamp = scheduler.next_review_timestamp

        output = [
            TermColor.bold('Adding flashcard')
        ]
        output.extend(
            flashcard.pformat(
                term_color=TermColor.light_blue
            )
        )
        await self.async_io.print_formatted_output(output)

        action_msgs = []
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
            flashcard.created = datetime_utc_now()
            self.db_session.add_flashcard(flashcard=flashcard)
            await self.async_io.print(TermColor.bold(f'Added: {flashcard}'))
        else:
            self.popleft_previous_sources()
            await self.async_io.print(TermColor.red('Aborting flashcard.'))

    async def show_duplicates(self, duplicates: List[Flashcard]):
        if duplicates:
            await self.async_io.print(
                TermColor.bold(f'Duplicate flashcards: {len(duplicates)}')
            )
            for dup in duplicates:
                await self.async_io.print_formatted_output(output=[
                    f'{TermColor.purple("Flashcard id:")} '
                    f'{dup["flashcard_id"]}',
                    f'{TermColor.purple("Question:")} '
                    f'{dup["side_question"]}',
                    f'{TermColor.purple("Answer:")} '
                    f'{dup["side_answer"]}',
                    f'{TermColor.purple("Review date:")} '
                    f'{convert_datetime_to_local(dup["review_timestamp"])}',
                    f'{TermColor.purple("Source:")} {dup["source"]}',
                    f'{TermColor.purple("Created:")} '
                    f'{convert_datetime_to_local(dup["created"])}'
                ])
