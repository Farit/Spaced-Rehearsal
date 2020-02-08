import os
import pathlib
import os.path

from typing import List

from src.mediator.general_mediator import GeneralMediator
from src.flashcard import Flashcard
from src.media_player import Player
from src.utils import get_human_readable_file_size, normalize_eng_word

from src.actions import (
    EnglishReviewAction,
    EnglishCreateAction,
    EnglishRussianCreateAction,
    EnglishAlterAction,
)


class EnglishMediator(GeneralMediator):

    def __init__(self, dictionary=None, text_to_speech=None):
        super().__init__()
        self.dictionary = dictionary
        self.text_to_speech = text_to_speech
        self.media_player = Player()

        # Set project root path.
        current_dir = os.path.dirname(__file__)
        root = os.path.abspath(os.path.join(current_dir, '../..'))
        self.project_root_path = pathlib.Path(root)

    @classmethod
    def name(cls):
        return 'english'

    def make_review_action(self):
        return EnglishReviewAction(mediator=self)

    def make_create_action(self):
        return EnglishCreateAction(mediator=self)

    def make_alter_action(self):
        return EnglishAlterAction(mediator=self)

    def get_audio_dir(self):
        return self.project_root_path.joinpath(f'audio/{self.name()}')

    async def exit(self):
        await super().exit()
        if self.dictionary:
            await self.dictionary.close()

    async def update_flashcard(self, flashcard: Flashcard):
        await super().update_flashcard(flashcard=flashcard)

    async def delete_flashcard(self, flashcard: Flashcard):
        await super().delete_flashcard(flashcard=flashcard)
        if flashcard.is_audio_type():
            audio_file = flashcard.get_audio_file(parent_dir=self.get_audio_dir())
            os.remove(str(audio_file))

    async def play_audio(self, audio_file_path):
        self.media_player.play(str(audio_file_path))

    async def input_phonetic_transcription(
        self, flashcard_answer, curr_ans_pronunciation=None
    ):
        pre_fill = curr_ans_pronunciation

        if self.dictionary is not None:
            await self.print(
                f'Please, wait a bit. Retrieving phonetic spellings.',
                bold=True
            )
            pronunciation = await self.dictionary.get_text_pronunciation(
                flashcard_answer
            )
            if pronunciation is not None:
                pre_fill = pronunciation

        phonetic_transcription = await self.input(
            'Phonetic transcription',
            pre_fill=pre_fill
        )
        return phonetic_transcription

    async def input_explanation(self, label='Explanation', pre_fill: str=None):
        recent_explanations = self.db_session.get_recent_explanations(
            user_id=self.get_user_id()
        )

        explanation = await self.input(
            label, pre_fill=pre_fill, history=recent_explanations
        )
        return explanation

    async def input_examples(self, data: List[str]=None):
        examples = []
        for example in data or []:
            example = await self.input('Example', pre_fill=example)
            if example:
                examples.append(example)

        while True:
            example = await self.input('Example')
            if example:
                examples.append(example)
            else:
                break

        return examples


class EnglishRussianMediator(EnglishMediator):

    def make_create_action(self):
        return EnglishRussianCreateAction(mediator=self)
