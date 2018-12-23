from src.flashcard import Flashcard
from src.actions.create_action.general_create_action import (
    GeneralCreateAction
)


class EnglishCreateAction(GeneralCreateAction):

    async def _create_flashcard(self):
        question = await self.mediator.input_question()
        answer = await self.mediator.input_answer()
        source = await self.mediator.input_source()
        phonetic_transcription = await self.mediator.input_phonetic_transcription(
            data=answer
        )
        explanation = await self.mediator.input_explanation()
        examples = await self.mediator.input_examples()

        flashcard: Flashcard = Flashcard.create(
            user_id=self.mediator.get_user_id(),
            flashcard_type=self.mediator.name(),
            question=question,
            answer=answer,
            source=source,
            phonetic_transcription=phonetic_transcription,
            explanation=explanation,
            examples=examples
        )
        return flashcard

