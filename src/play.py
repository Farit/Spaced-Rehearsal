from datetime import datetime

from src.db_session import DBSession
from src.config import ConfigAdapter
from src.utils import TermColor, normalize_value
from src.base import AsyncIO
from src.flashcard import Flashcard
from src.text_to_speech import TextToSpeech
from src.media_player import Player
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

            audio_file = TextToSpeech(flashcard=flashcard).synthesize_audio()

            if audio_file:
                action = await self.get_action_with_audio(
                    flashcard=flashcard,
                    audio_file=audio_file
                )
            else:
                action = await self.get_action_without_audio(
                    flashcard=flashcard
                )

            if action == 'q':
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
        ]
        output.extend(
            flashcard.pformat(
                term_color=TermColor.grey,
                exclude_fields=['side_question']
            )
        )
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

    async def get_action_without_audio(self, flashcard):
        action = await self.async_io.input_action(
            action_answers=('c', 'q'),
            action_msgs=[
                f'Do you want to continue, '
                f'continue [{TermColor.green("c")}], '
                f'quit [{TermColor.red("q")}]?'
            ]
        )
        return action

    async def get_action_with_audio(self, flashcard, audio_file):
        while True:
            output = ["Do you want to hear how to pronounce?"]
            output.extend(
                flashcard.pformat(
                    term_color=TermColor.light_blue,
                    include_fields=[
                        'side_answer',
                        'phonetic_transcriptions'
                    ]
                )
            )
            await self.async_io.print_formatted_output(output)

            action = await self.async_io.input_action(
                action_answers=('y', 'c', 'q'),
                action_msgs=[
                    f'Please enter, '
                    f'yes [{TermColor.light_blue("y")}], '
                    f'continue [{TermColor.green("c")}], '
                    f'quit [{TermColor.red("q")}]'
                ]
            )

            if action == 'y':
                Player(audio_file=audio_file).play()
            else:
                return action
