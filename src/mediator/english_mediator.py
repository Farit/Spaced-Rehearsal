import os
import pathlib
import os.path

from typing import List

from src.mediator.base_mediator import Mediator
from src.flashcard import Flashcard
from src.text_to_speech import TextToSpeech
from src.media_player import Player
from src.utils import get_human_readable_file_size, normalize_eng_word

from src.actions import (
    EnglishReviewAction,
    EnglishCreateAction,
    EnglishAlterAction,
)


class EnglishMediator(Mediator):

    def __init__(self, dictionary=None):
        super().__init__()
        self.dictionary = dictionary
        self.text_to_speech = TextToSpeech(
            lang=TextToSpeech.Lang.ENG,
            config=self.config
        )
        self.media_player = Player()

    @classmethod
    def name(cls):
        return 'english'

    @property
    def project_root_path(self) -> pathlib.Path:
        current_dir = os.path.dirname(__file__)
        root = os.path.abspath(os.path.join(current_dir, '../..'))
        return pathlib.Path(root)

    def make_review_action(self):
        return EnglishReviewAction(mediator=self)

    def make_create_action(self):
        return EnglishCreateAction(mediator=self)

    def make_alter_action(self):
        return EnglishAlterAction(mediator=self)

    async def save_flashcard(self, flashcard: Flashcard):
        await super().save_flashcard(flashcard=flashcard)

    async def update_flashcard(self, flashcard: Flashcard):
        await super().update_flashcard(flashcard=flashcard)

    async def delete_flashcard(self, flashcard: Flashcard):
        await super().delete_flashcard(flashcard=flashcard)
        await self._remove_audio_answer(flashcard)

    async def attach_audio_answer(
        self, flashcard: Flashcard, audio_answer_url: str=None
    ):
        await self.print('Downloading audio answer...')

        if audio_answer_url is not None:
            file_data = await self.text_to_speech.download_audio(
                url=audio_answer_url
            )
        else:
            file_data = await self.text_to_speech.synthesize_audio(
                text=flashcard.answer
            )

        if file_data:
            fp = self._form_audio_answer_file_path(flashcard)
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_bytes(file_data)

            await self.print(f'Saved audio answer:')
            relative_file_path = fp.relative_to(self.project_root_path)
            await self.print(f'    File path: {relative_file_path}')
            file_size = get_human_readable_file_size(fp.stat().st_size)
            await self.print(f'    File size: {file_size}', bottom_margin=1)
        else:
            await self.print(f"Couldn't get audio answer", bottom_margin=1)

    async def play_audio_answer(self, flashcard):
        audio_file_path = self._form_audio_answer_file_path(flashcard)
        self.media_player.play(str(audio_file_path))

    async def has_audio_answer(self, flashcard) -> bool:
        fp = self._form_audio_answer_file_path(flashcard)
        return fp.exists()

    async def _remove_audio_answer(self, flashcard):
        fp = self._form_audio_answer_file_path(flashcard)
        if fp.exists():
            os.remove(str(fp))
            os.rmdir(str(fp.parent))

    def _form_audio_answer_file_path(self, flashcard) -> pathlib.Path:
        audio_file_path = (
            f'audio/{self.name()}/{flashcard.id}/'
            f'audio_{flashcard.id}.mp3'
        )
        return self.project_root_path.joinpath(audio_file_path)

    async def input_phonetic_transcription(
        self, flashcard_answer, curr_ans_pronunciation=None
    ):
        pre_fill = curr_ans_pronunciation

        pronunciation = await self.get_pronunciation(flashcard_answer)
        if pronunciation is not None:
            pre_fill = pronunciation

        phonetic_transcription = await self.input(
            'Phonetic transcription',
            pre_fill=pre_fill
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

    async def get_pronunciation(self, flashcard_answer):
        if self.dictionary is not None:
            await self.print(
                f'Please, wait a bit. Retrieving phonetic spellings.',
                bold=True
            )
            err_codes = self.dictionary.error_codes
            pronunciations = []

            for word in flashcard_answer.split():
                normalized_word = normalize_eng_word(word)

                res = await self.dictionary.get_pronunciation(normalized_word)
                pron, err = res['pronunciation'], res['error']

                if pron is None and err is err_codes.CANNOT_FIND_IN_DICT:

                    res = await self.dictionary.get_lemmas(normalized_word)
                    lemmas, err = res['lemmas'], res['error']
                    if lemmas:
                        res = await self.dictionary.get_pronunciation(lemmas[0])
                        pron, err = res['pronunciation'], res['error']

                pronunciations.append((normalized_word, f'/{pron}/'))
            return '   '.join(f'{w}: {p}' for w, p in pronunciations)
