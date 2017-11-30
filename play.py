import random

from datetime import datetime, timedelta

from db_session import DBSession
from config import ConfigAdapter
from utils import TermColor, normalize_value
from base import AsyncIO


class Play:
    def __init__(self, user_id: int, async_io: AsyncIO):
        self.total = 0
        self.count = 0
        self.played = 0
        self.right = 0
        self.wrong = 0
        self.timeout = 0
        self.user_id = user_id
        self.config = ConfigAdapter(filename='config.cfg')
        self.db_session = DBSession(self.config['database'].get('name'))
        self.async_io = async_io

    async def play(self):
        flashcards = self.db_session.get_ready_flashcards(user_id=self.user_id)
        random.shuffle(flashcards)
        self.total = len(flashcards)

        for flashcard in flashcards:
            self.count += 1
            await self._play_flashcard(flashcard)
            self.played += 1

            if self.played < self.total:
                action = await self.async_io.input_action(
                    action_answers=('y', 'n'),
                    action_msgs=[
                        (
                            f'Do you want to continue '
                            f'[{TermColor.green("y")}/{TermColor.red("n")}] ?',
                        )
                    ]
                )
                if action == 'n':
                    break

        await self.print_game_score()

    async def _play_flashcard(self, flashcard):
        header = f'Flashcard[{flashcard["id"]}] #{self.count} / #{self.total}'
        await self.async_io.print(TermColor.bold(header))

        show_side_a = f'{TermColor.grey("Side A: ")}{flashcard["side_a"]}'
        await self.async_io.print(show_side_a)

        start_time = datetime.now()
        entered_side_b = await self.async_io.input('Side B')
        end_time = datetime.now()

        is_timeout = (end_time - start_time) > timedelta(
            seconds=self.config.getint('play', 'answer_timeout')
        )

        entered_side_b = normalize_value(entered_side_b)
        flashcard_side_b = normalize_value(flashcard['side_b'])

        if entered_side_b.lower() == flashcard_side_b.lower():
            if is_timeout:
                result = TermColor.red('Timeout')
                box = 0
                self.timeout += 1
            else:
                result = TermColor.green('Right')
                box = flashcard['box'] + 1
                self.right += 1
        else:
            result = TermColor.red('Wrong')
            box = 0
            self.wrong += 1

        due = datetime.now() + timedelta(days=2**box)
        self.db_session.update_flashcard(
            due=due, box=box, flashcard_id=flashcard['id']
        )

        await self.async_io.print(
            f'{TermColor.grey("Answer: ")}{flashcard["side_b"]} {result}',
            f'{TermColor.grey("Source: ")}{flashcard["source"] or ""}',
            f'{TermColor.grey("Phonetic transcriptions: ")}'
            f'{flashcard["phonetic_transcriptions"] or ""}',
            f'{TermColor.grey("Explanation: ")}'
            f'{flashcard["explanation"] or ""}',
            f'{TermColor.grey("Examples: ")}{flashcard["examples"] or ""}'
        )

    async def print_game_score(self):
        await self.async_io.print(
            f'Total: {self.total}, '
            f'Played: {self.played}, '
            f'Right: {self.right}, '
            f'Wrong: {self.wrong}, '
            f'Timeout: {self.timeout}',
            f'Game is over!'
        )
