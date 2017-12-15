import textwrap
import random

from datetime import datetime, timedelta

from src.db_session import DBSession
from src.config import ConfigAdapter
from src.utils import TermColor, normalize_value, datetime_utc_now
from src.base import AsyncIO


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

    def counters_zeroing(self):
        self.total = 0
        self.count = 0
        self.played = 0
        self.right = 0
        self.wrong = 0
        self.timeout = 0

    async def play(self):
        self.counters_zeroing()
        start_time = datetime.now()
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
                        f'Do you want to continue '
                        f'[{TermColor.green("y")}/{TermColor.red("n")}] ?',
                    ]
                )
                if action == 'n':
                    break

        end_time = datetime.now()
        playing_time = end_time - start_time
        await self.print_game_score(playing_time)

    async def _play_flashcard(self, flashcard):
        header = f'Flashcard[{flashcard["id"]}] #{self.count} / #{self.total}'
        await self.async_io.print(TermColor.bold(header))
        await self.print_flashcard_side_a(flashcard)

        start_time = datetime.now()
        entered_side_b = await self.async_io.input('Side B')
        end_time = datetime.now()

        is_timeout = (end_time - start_time) > timedelta(
            seconds=self.config.getint('play', 'answer_timeout')
        )

        entered_side_b = normalize_value(
            entered_side_b, remove_trailing='.', to_lower=True
        )
        flashcard_side_b = normalize_value(
            flashcard['side_b'], remove_trailing='.', to_lower=True
        )

        if entered_side_b == flashcard_side_b:
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

        due = datetime_utc_now() + timedelta(days=2**box)
        self.db_session.update_flashcard(
            due=due, box=box, flashcard_id=flashcard['id']
        )

        await self.print_flashcard_score(flashcard, result)

    async def print_flashcard_side_a(self, flashcard):
        await self.async_io.print_formatted_output(output=[
            f'{TermColor.grey("Side A: ")}{flashcard["side_a"]}'
        ])

    async def print_flashcard_score(self, flashcard, result):
        output = [
            f'{TermColor.grey("Result: ")}{result}',
            f'{TermColor.grey("Answer: ")}{flashcard["side_b"]}',
        ]

        source = (flashcard["source"] or "").strip()
        if source:
            output.append(
                f'{TermColor.grey("Source: ")}{source}'
            )

        phonetic_trans = (flashcard["phonetic_transcriptions"] or "").strip()
        if phonetic_trans:
            output.append(
                f'{TermColor.grey("Phonetic transcriptions: ")}{phonetic_trans}'
            )

        explanation = (flashcard["explanation"] or "").strip()
        if explanation:
            output.append(
                f'{TermColor.grey("Explanation: ")}{explanation}'
            )

        examples = (flashcard["examples"] or "").strip()
        if examples:
            output.append(f'{TermColor.grey("Examples: ")}')
            examples = examples.split(';')
            examples.sort(reverse=True)
            for ind, example in enumerate(examples, start=1):
                example = example.strip()
                if example:
                    formated_example = f'{ind}: {example}'
                    output.append(textwrap.indent(formated_example, ' '*4))

        await self.async_io.print_formatted_output(output)

    async def print_game_score(self, playing_time=None):
        output = []
        if playing_time is not None:
            output.append(
                f'Playing time: {playing_time}'
            )
        output.extend([
            f'Total: {self.total}, '
            f'Played: {self.played}, ',
            f'Right: {self.right}, '
            f'Wrong: {self.wrong}, '
            f'Timeout: {self.timeout}',
            f'Game is over!'
        ])
        await self.async_io.print(*output)
