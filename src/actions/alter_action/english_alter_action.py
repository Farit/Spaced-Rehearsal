from src.flashcard import Flashcard
from src.actions.alter_action.general_alter_action import GeneralAlterAction


class EnglishAlterAction(GeneralAlterAction):

    async def _alter_flashcard(self, flashcard: Flashcard):
        question = await self.mediator.input_question(
            pre_fill=flashcard.question
        )
        answer = await self.mediator.input_answer(
            pre_fill=flashcard.answer
        )
        source = await self.mediator.input_source(
            pre_fill=flashcard.source
        )
        phonetic_transcription = await self.mediator.input_phonetic_transcription(
            data=answer
        )
        explanation = await self.mediator.input_explanation(
            pre_fill=flashcard.explanation
        )
        examples = await self.mediator.input_examples(
            data=flashcard.examples
        )

        flashcard.alter(
            question=question,
            answer=answer,
            source=source,
            phonetic_transcription=phonetic_transcription,
            explanation=explanation,
            examples=examples
        )
