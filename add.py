from collections import deque
from datetime import timedelta

from db_session import DBSession
from flashcard import Flashcard
from utils import TermColor, Communication, datetime_utc_now
from base import BaseClass


class AddFlashcard(BaseClass):

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.previous_sources = deque([None], maxlen=2)
        self.db_session = DBSession(self.config['database'].get('name'))

    def add(self):
        flashcard = Flashcard(user_id=self.user_id)
        Communication.print_output(TermColor.bold('Add new flashcard:'))

        flashcard.side_a = Communication.print_input('Side A')
        flashcard.side_b = Communication.print_input('Side B')

        source = Communication.print_input('Source')
        if source.strip() == '\p':
            source = self.previous_sources[0]
        else:
            self.previous_sources.appendleft(source)
        flashcard.source = source

        flashcard.phonetic_transcriptions = Communication.print_input(
            'Phonetic transcriptions'
        )

        part_of_speech = Communication.print_input('Part of speech')
        explanation = Communication.print_input('Explanation')
        flashcard.explanation = f'[{part_of_speech}] {explanation}'

        flashcard.examples = Communication.print_input('Examples(;)')

        duplicates = self.db_session.get_flashcard_duplicates(flashcard)
        self.show_duplicates(duplicates)

        flashcard.due = datetime_utc_now() + timedelta(days=2**flashcard.box)

        action = self.request_input(
            request_answers=('y', 'n'),
            request_msgs=[
                (
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
                    f'{TermColor.ligth_blue("Examples:")} {flashcard.examples}'
                ),
                (
                    f'Duplicates: {len(duplicates)}',
                    f'Do you want to add '
                    f'[{TermColor.green("y")}/{TermColor.red("n")}] ?',
                )
            ]
        )

        if action == 'y':
            self.db_session.add_flashcard(flashcard=flashcard)
            Communication.print_output(TermColor.bold(f'Added: {flashcard}'))
        else:
            Communication.print_output(TermColor.red('Aborting flashcard.'))

    @staticmethod
    def show_duplicates(duplicates):
        if duplicates:
            Communication.print_output(
                TermColor.bold(f'Duplicate flashcards: {len(duplicates)}')
            )
            for duplicate in duplicates:
                Communication.print_output(
                    f'Side A: {duplicate["side_a"]}',
                    f'Side B: {duplicate["side_b"]}',
                    f'Box: {duplicate["box"]}',
                    f'Due: {duplicate["due"]}',
                    f'User: {duplicate["user_id"]}',
                    f'Source: {duplicate["source"]}',
                    f'Created: {duplicate["created"]}'
                )
