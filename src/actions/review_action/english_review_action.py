from src.flashcard import Flashcard
from src.actions.review_action.general_review_action import GeneralReviewAction


class EnglishReviewAction(GeneralReviewAction):

    async def make_review(self, flashcard: Flashcard, review_stat):
        await super().make_review(flashcard, review_stat)
        await self.play_audio_answer(flashcard)

    async def play_audio_answer(self, flashcard: Flashcard):
        has_audio_answer = await self.mediator.has_audio_answer(flashcard)
        while True and has_audio_answer:

            confirmed: bool = await self.mediator.input_confirmation(
                f'Do you want to hear how to pronounce?',
                f'{self.mediator.format_green("Answer")}: {flashcard.answer}',
                f'{self.mediator.format_green("Phonetic transcription")}: '
                f'{flashcard.phonetic_transcription}'
            )
            if confirmed:
                await self.mediator.play_audio_answer(flashcard)
            else:
                break

