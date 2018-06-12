from collections import deque
from typing import List

from src.db_session import DBSession
from src.flashcard import Flashcard
from src.config import ConfigAdapter
from src.utils import TermColor, datetime_now, normalize_value
from src.base import AsyncIO
from src.scheduler import FlashcardScheduler
from src.dictionary import Dictionary


class CreateFlashcard:

    def __init__(self, user_id, async_io: AsyncIO):
        self.user_id = user_id
        self.previous_sources = deque([], maxlen=5)
        self.config = ConfigAdapter(filename='config.cfg')
        self.db_session = DBSession(self.config['database'].get('name'))
        self.async_io = async_io
        self.source_tags = self.get_source_tags()
        self.dictionary = Dictionary()

    def get_source_tags(self):
        tags = self.db_session.get_flashcard_source_tags(self.user_id)
        source_tags = {
            normalize_value(tag.strip(), remove_trailing='.').capitalize() + '.'
            for tag in tags if tag and tag.strip()
        }
        return source_tags

    async def update_source_tags(self, tag=None):
        if tag is not None:
            self.source_tags.add(
                normalize_value(tag.strip(), remove_trailing='.').capitalize() 
                + '.'
            )
        else:
            self.source_tags = self.get_source_tags()

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
            pre_fill=self.previous_sources[0] if self.previous_sources else '',
            history=self.source_tags
        )
        self.previous_sources.appendleft(source)
        await self.update_source_tags(source)
        flashcard.source = source

        await self.input_phonetic_spelling(flashcard)

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

        duplicates = self.db_session.search(
            flashcard.side_answer,
            flashcard.side_question,
            user_id=flashcard.user_id
        )
        await self.show_duplicates(duplicates)

        if flashcard.side_answer:
            scheduler = FlashcardScheduler(
                flashcard_answer_side=flashcard.side_answer
            )
            scheduler.to_init()
            flashcard.state = scheduler.next_state
            flashcard.review_timestamp = scheduler.next_review_timestamp

        flashcard.created = datetime_now()

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
                f'{TermColor.purple(f"Possible duplicates: {len(duplicates)}")}'
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
            self.popleft_previous_sources()
            await self.async_io.print(TermColor.red('Aborting flashcard.'))

    async def input_phonetic_spelling(self, flashcard):
        await self.async_io.print(
            f'Please, wait a bit. Retrieving phonetic spellings.'
        )
        spellings = {}
        answer_spelling = []
        for word in flashcard.side_answer.split(' '):
            if word.lower() not in spellings:
                spelling = await self.dictionary.get_word_phonetic_spelling(word)
                spellings[word.lower()] = f'/{spelling}/' if spelling else ''

            answer_spelling.append(
                (word, spellings[word.lower()])
            )

        pre_fill = ' '.join(f'{k} {v}' for k, v in answer_spelling)

        flashcard.phonetic_transcriptions = await self.async_io.input(
            'Phonetic transcriptions',
            pre_fill=pre_fill
        )

    async def show_duplicates(self, duplicates: List[Flashcard]):
        if duplicates:
            await self.async_io.print(
                TermColor.bold(
                    f'Possible duplicate flashcards: {len(duplicates)}'
                )
            )
            for dup in duplicates:
                output = [
                    f'{TermColor.purple("Flashcard id:")} '
                    f'{dup["flashcard_id"]}',
                ]
                output.extend(
                    dup.pformat(
                        term_color=TermColor.purple
                    )
                )
                await self.async_io.print_formatted_output(output)
