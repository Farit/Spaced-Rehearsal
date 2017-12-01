import textwrap
import random

from datetime import datetime, timedelta

from db_session import DBSession
from config import ConfigAdapter
from utils import TermColor, normalize_value, datetime_utc_now
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
                        f'Do you want to continue '
                        f'[{TermColor.green("y")}/{TermColor.red("n")}] ?',
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
            for ind, example in enumerate(examples.split(';'), start=1):
                formated_example = f'{ind}: {example}'
                output.append(textwrap.indent(formated_example, ' '*4))

        formated_output = []
        for line in output:
            output_lines = textwrap.wrap(line, width=100)
            for ind, output_line in enumerate(output_lines):
                if ind == 0:
                    formated_output.append(output_line)
                else:
                    formated_output.append(textwrap.indent(output_line, ' '*4))

        await self.async_io.print(*formated_output)

    async def print_game_score(self):
        await self.async_io.print(
            f'Total: {self.total}, '
            f'Played: {self.played}, '
            f'Right: {self.right}, '
            f'Wrong: {self.wrong}, '
            f'Timeout: {self.timeout}',
            f'Game is over!'
        )
