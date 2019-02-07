from src.flashcard import Flashcard
from src.actions.review_action.general_review_action import GeneralReviewAction


class EnglishReviewAction(GeneralReviewAction):
    
    async def process_flashcard(self, counter, flashcard: Flashcard, review_stat):
        await self.mediator.print(
            f'Flashcard[{flashcard.id}] #{counter} / #{review_stat.total}',
            bold=True
        )
        await self.make_review(flashcard, review_stat)
        has_audio_answer = await self.mediator.has_audio_answer(flashcard)
        can_continue = True

        if not has_audio_answer:
            can_continue: bool = await self.mediator.input_confirmation(
                'Do you want to continue?'
            )
        else:
            while True:
                action = await self.mediator.input_action(
                    action_answers=('y', 'c', 'q'),
                    action_msgs=[
                        f'If you want to hear how to pronounce',
                        f'{self.mediator.format_green("Phonetic transcription")}: '
                        f'{flashcard.phonetic_transcription}',
                        f'Please, enter '
                        f'{self.mediator.format_green("y")}.',

                        '',

                        f'If you want to continue, '
                        f'enter {self.mediator.format_yellow("c")}.',

                        f'If you want to quit, '
                        f'enter {self.mediator.format_red("q")}.'
                    ]
                )
                if action in ['c', 'q']:
                    can_continue = True if action == 'c' else False
                    break

                await self.mediator.play_audio_answer(flashcard)

        return can_continue
