from src.db_session import DBSession
from src.config import ConfigAdapter
from src.utils import TermColor
from src.search import Search
from src.base import AsyncIO


class AlterFlashcard:

    def __init__(self, user_id, async_io: AsyncIO):
        self.user_id = user_id
        self.config = ConfigAdapter(filename='config.cfg')
        self.db_session = DBSession(self.config['database'].get('name'))
        self.async_io = async_io
        self.search = Search(
            user_id=user_id, async_io=self.async_io
        )

    async def alter(self):
        await self.async_io.print(
            TermColor.bold('Alter Flashcard'),
            f'Pressing {TermColor.red("Ctrl+D")} terminates altering.'
        )

        flashcards = await self.search()

        if flashcards:
            flashcards = {
                str(f.flashcard_id): f for f in flashcards
            }

            action_msgs =[
                f'Please, enter flashcard {TermColor.bold("id")} '
                f'you want to {TermColor.underline("alter")}.',
                f'If you want to exit, please enter {TermColor.red("q")}'
            ]
            action = await self.async_io.input_action(
                action_answers=tuple(list(flashcards.keys()) + ['q']),
                action_msgs=action_msgs
            )

            if action != 'q':
                flashcard = await self.alter_flashcard(
                    flashcard=flashcards[action]
                )
                await self.show_flashcard(flashcard)

                action_msgs = [
                    f'Do you want to alter '
                    f'[{TermColor.green("y")}/{TermColor.red("n")}] ?',
                ]

                action = await self.async_io.input_action(
                    action_answers=('y', 'n'), action_msgs=action_msgs
                )

                if action == 'y':
                    self.db_session.update_flashcard(flashcard=flashcard)
                    await self.async_io.print(
                        TermColor.bold(f'Altered: {flashcard}')
                    )
                else:
                    await self.async_io.print(
                        TermColor.red('Aborting altering.')
                    )

    async def alter_flashcard(self, flashcard):
        await self.async_io.print(
            TermColor.bold(
                f'Altering Flashcard[{flashcard.flashcard_id}]'
            )
        )

        flashcard.side_question = await self.async_io.input(
            'Question',
            pre_fill=flashcard.side_question
        )
        flashcard.side_answer = await self.async_io.input(
            'Answer',
            pre_fill=flashcard.side_answer
        )
        flashcard.source = await self.async_io.input(
            'Source',
            pre_fill=flashcard.source
        )
        flashcard.phonetic_transcriptions = await self.async_io.input(
            'Phonetic transcriptions',
            pre_fill=flashcard.phonetic_transcriptions
        )
        flashcard.explanation = await self.async_io.input(
            'Explanation',
            pre_fill=flashcard.explanation
        )

        examples = []
        for example in flashcard.get_examples():
            example = await self.async_io.input(
                'Example', pre_fill=example
            )
            if example:
                examples.append(example)

        while True:
            example = await self.async_io.input('Example')
            if example:
                examples.append(example)
            else:
                break

        flashcard.set_examples(examples)
        return flashcard

    async def show_flashcard(self, flashcard):
        output = [
            TermColor.bold('Altered flashcard')
        ]
        output.extend(
            flashcard.pformat(
                term_color=TermColor.light_blue
            )
        )
        await self.async_io.print_formatted_output(output)
