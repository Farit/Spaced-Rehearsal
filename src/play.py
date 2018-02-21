import textwrap

from datetime import datetime

from src.db_session import DBSession
from src.config import ConfigAdapter
from src.utils import TermColor, normalize_value, convert_datetime_to_local
from src.base import AsyncIO
from src.flashcard import Flashcard
from src.scheduler import FlashcardScheduler


class Play:
    def __init__(self, user_id: int, async_io: AsyncIO):
        self.user_id = user_id
        self.config = ConfigAdapter(filename='config.cfg')
        self.db_session = DBSession(self.config['database'].get('name'))
        self.async_io = async_io
        self.stats = None

    async def play(self):
        flashcards = self.db_session.get_ready_flashcards(user_id=self.user_id)
        self.stats = {
            'start_time': datetime.now(),
            'total': len(flashcards),
            'count': 0,
            'played': 0,
            'right': 0,
            'wrong': 0
        }

        await self.async_io.print(
            f'Pressing {TermColor.red("Ctrl+D")} terminates playing.'
        )
        for flashcard in flashcards:
            self.stats['count'] += 1
            await self._play_flashcard(flashcard)
            self.stats['played'] += 1

            if self.stats['played'] < self.stats['total']:
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

    async def _play_flashcard(self, flashcard: Flashcard):
        scheduler = FlashcardScheduler(
            flashcard_answer_side=flashcard.side_answer,
            current_state=flashcard.state,
            current_review_timestamp=flashcard.review_timestamp
        )

        await self.async_io.print(TermColor.bold(
            f'Flashcard[{flashcard.flashcard_id}] '
            f'#{self.stats["count"]} / #{self.stats["total"]}'
        ))
        await self.async_io.print_formatted_output(output=[
            f'{TermColor.grey("Question: ")}{flashcard["side_question"]}'
        ])

        entered_answer = await self.async_io.input('Answer')
        entered_answer = normalize_value(
            entered_answer, remove_trailing='.', to_lower=True
        )
        flashcard_side_answer = normalize_value(
            flashcard['side_answer'], remove_trailing='.', to_lower=True
        )

        if entered_answer == flashcard_side_answer:
            scheduler.to_success()
            self.stats['right'] += 1
            result = TermColor.green('Right')
        else:
            scheduler.to_failure()
            self.stats['wrong'] += 1
            result = TermColor.red('Wrong')

        flashcard.state = scheduler.next_state
        flashcard.review_timestamp = scheduler.next_review_timestamp

        self.db_session.update_flashcard_state(flashcard)
        await self.print_flashcard_score(flashcard, result)

    async def print_flashcard_score(self, flashcard, result):
        output = [
            f'{TermColor.grey("Result: ")}{result}',
            f'{TermColor.grey("Answer: ")}{flashcard["side_answer"]}',
            f'{TermColor.grey("Next review: ")}'
            f'{convert_datetime_to_local(flashcard["review_timestamp"])}',
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

        examples = flashcard.get_examples()
        if examples:
            output.append(f'{TermColor.grey("Examples: ")}')
            examples.sort(reverse=True)
            for ind, example in enumerate(examples, start=1):
                example = example.strip()
                if example:
                    formatted_example = f'{ind}: {example}'
                    output.append(textwrap.indent(formatted_example, ' '*4))

        await self.async_io.print_formatted_output(output)

    async def print_game_score(self):
        output = []
        end_time = datetime.now()
        if self.stats is not None:
            playing_time = end_time - self.stats['start_time']
            output.extend([
                f'Playing time: {playing_time}'
            ])
            for stat_key in ['total', 'played', 'right', 'wrong']:
                key = f'{stat_key}:'.title().ljust(10)
                value = str(self.stats[stat_key]).rjust(6)
                output.append(f'{key}{value}')

        output.append(f'Game is over!')
        await self.async_io.print(*output)
