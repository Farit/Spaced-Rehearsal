import random

from datetime import datetime, timedelta

from db_session import DBSession
from utils import TermColor, Communication, normalize_value
from base import BaseClass


class Play(BaseClass):

    def __init__(self, user_id):
        super().__init__()
        self.total = 0
        self.count = 0
        self.played = 0
        self.right = 0
        self.wrong = 0
        self.timeout = 0
        self.user_id = user_id
        self.db_session = DBSession(self.config['database'].get('name'))

    def __call__(self):
        flashcards = self.db_session.get_ready_flashcards(user_id=self.user_id)
        random.shuffle(flashcards)
        self.total = len(flashcards)

        for flashcard in flashcards:
            self.count += 1
            side_b, flashcard_side_b, is_timeout = self.play(flashcard)
            result = self.handle_answer(
                flashcard, side_b, flashcard_side_b, is_timeout
            )
            self.print_result(flashcard, result)
            self.played += 1

            if self.played < self.total:
                action = self.request_input(
                    request_answers=('y', 'n'),
                    request_msgs=[
                        (
                            f'Do you want to continue '
                            f'[{TermColor.green("y")}/{TermColor.red("n")}] ?',
                        )
                    ]
                )
                if action == 'n':
                    break

        self.print_end()

    def play(self, flashcard):
        Communication.print_output(
            TermColor.bold(
                f'Flashcard[{flashcard["id"]}] #{self.count} / #{self.total}')
        )
        Communication.print_play_output(
            key='Side A', value=f'{flashcard["side_a"]}'
        )
        start_time = datetime.now()
        side_b = Communication.print_play_input(key='Side B')
        end_time = datetime.now()
        is_timeout = (end_time - start_time) > timedelta(
            seconds=self.config.getint('play', 'answer_timeout')
        )

        side_b = normalize_value(side_b)
        flashcard_side_b = normalize_value(flashcard['side_b'])

        return side_b, flashcard_side_b, is_timeout

    def handle_answer(self, flashcard, side_b, flashcard_side_b, is_timeout):
        if side_b.lower() == flashcard_side_b.lower():
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
        return result

    @staticmethod
    def print_result(flashcard, result):
        Communication.print_play_output(
            key='Answer',
            value=f'{flashcard["side_b"]} {result}'
        )
        Communication.print_play_output(
            key='Source',
            value=f'{flashcard["source"] or ""}'
        )
        Communication.print_play_output(
            key='Phonetic transcriptions',
            value=f'{flashcard["phonetic_transcriptions"] or ""}'
        )
        Communication.print_play_output(
            key='Explanation',
            value=f'{flashcard["explanation"] or ""}'
        )
        Communication.print_play_output(
            key='Examples',
            value=f'{flashcard["examples"] or ""}'
        )

    def print_end(self, with_start_new_line=False):
        Communication.print_output(
            f'Total: {self.total}, '
            f'Played: {self.played}, '
            f'Right: {self.right}, '
            f'Wrong: {self.wrong}, '
            f'Timeout: {self.timeout}',
            f'Game is over!',
            with_start_new_line=with_start_new_line
        )
