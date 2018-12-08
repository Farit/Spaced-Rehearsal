import os
import path
import os.path

from typing import List

from src.mediator.base_mediator import Mediator
from src.flashcard import Flashcard
from src.dictionary import Dictionary
from src.text_to_speech import TextToSpeech
from src.media_player import Player

from src.actions import (
    EnglishReviewAction,
    EnglishCreateAction,
    EnglishAlterAction,
)


class EnglishMediator(Mediator):

    def __init__(self):
        super().__init__()
        self.dictionary = Dictionary(lang=Dictionary.Lang.ENG)
        self.text_to_speech = TextToSpeech(lang=TextToSpeech.Lang.ENG)
        self.media_player = Player()

    @classmethod
    def name(cls):
        return 'english'

    def make_review_action(self):
        return EnglishReviewAction(mediator=self)

    def make_create_action(self):
        return EnglishCreateAction(mediator=self)

    def make_alter_action(self):
        return EnglishAlterAction(mediator=self)

    async def save_flashcard(self, flashcard: Flashcard):
        await super().save_flashcard(flashcard=flashcard)
        await self._download_audio_answer(flashcard)

    async def update_flashcard(self, flashcard: Flashcard):
        await super().update_flashcard(flashcard=flashcard)
        await self._download_audio_answer(flashcard)

    async def delete_flashcard(self, flashcard: Flashcard):
        await super().delete_flashcard(flashcard=flashcard)
        await self._remove_audio_answer(flashcard)

    async def play_audio_answer(self, flashcard):
        audio_file_path = self._form_audio_answer_file_path(flashcard)
        if os.path.isfile(audio_file_path):
            self.media_player.play(audio_file_path)

    async def has_audio_answer(self, flashcard):
        fp = path.Path(self._form_audio_answer_file_path(flashcard))
        return fp.exists()

    async def _download_audio_answer(self, flashcard):
        await self.print('Downloading audio answer...')
        file_data = await self.text_to_speech.synthesize_audio(
            text=flashcard.answer
        )
        if file_data:
            fp = path.Path(self._form_audio_answer_file_path(flashcard))
            fp.dirname().makedirs_p()
            await self.print(f'Saving audio answer: {fp}')
            with open(fp, 'wb') as fh:
                fh.write(file_data)

    async def _remove_audio_answer(self, flashcard):
        fp = path.Path(self._form_audio_answer_file_path(flashcard))
        if fp.exists():
            os.remove(fp)
            os.rmdir(fp.dirname())

    def _form_audio_answer_file_path(self, flashcard):
        root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../..')
        )
        audio_file_path = (
            f'audio/{self.name()}/{flashcard.id}/'
            f'audio_{flashcard.id}.wav'
        )
        return os.path.join(root, audio_file_path)

    async def input_phonetic_transcription(self, data):
        await self.print(
            f'Please, wait a bit. Retrieving phonetic spellings.',
            bold=True
        )
        spellings = {}
        data_spelling = []

        for word in data.split(' '):
            if word.lower() not in spellings:
                spelling = await self.dictionary.get_word_phonetic_spelling(
                    word
                )
                spellings[word.lower()] = f'/{spelling}/' if spelling else ''

            data_spelling.append(
                (word, spellings[word.lower()])
            )

        pre_fill = ' '.join(f'{k} {v}' for k, v in data_spelling)

        phonetic_transcription = await self.input(
            'Phonetic transcription', pre_fill=pre_fill
        )
        return phonetic_transcription
 
    async def input_explanation(self, pre_fill: str=None):
        explanation = await self.input(
            'Explanation', pre_fill=pre_fill
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

