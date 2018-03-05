from src.db_session import DBSession
from src.config import ConfigAdapter
from src.utils import TermColor
from src.search import Search
from src.base import AsyncIO


class DeleteFlashcard:

    def __init__(self, user_id, async_io: AsyncIO):
        self.user_id = user_id
        self.config = ConfigAdapter(filename='config.cfg')
        self.db_session = DBSession(self.config['database'].get('name'))
        self.async_io = async_io
        self.search = Search(
            user_id=user_id, async_io=self.async_io
        )

    async def delete(self):
        await self.async_io.print(
            TermColor.bold('Delete Flashcard'),
            f'Pressing {TermColor.red("Ctrl+D")} terminates deleting.'
        )

        flashcards = await self.search()

        if flashcards:
            flashcards = {
                str(f.flashcard_id): f for f in flashcards
            }

            action_msgs =[
                f'Please, enter flashcard {TermColor.bold("id")} '
                f'you want to {TermColor.underline("delete")}.',
                f'If you want to exit, please enter {TermColor.red("q")}'
            ]
            action = await self.async_io.input_action(
                action_answers=tuple(list(flashcards.keys()) + ['q']),
                action_msgs=action_msgs
            )

            if action != 'q':
                flashcard = flashcards[action]
                await self.show_flashcard(flashcard)

                action_msgs = [
                    f'Do you want to delete '
                    f'[{TermColor.green("y")}/{TermColor.red("n")}] ?',
                ]

                action = await self.async_io.input_action(
                    action_answers=('y', 'n'), action_msgs=action_msgs
                )

                if action == 'y':
                    self.db_session.delete_flashcard(flashcard=flashcard)
                    await self.async_io.print(
                        TermColor.bold(f'Deleted: {flashcard}')
                    )
                else:
                    await self.async_io.print(
                        TermColor.red('Aborting deleting.')
                    )

    async def show_flashcard(self, flashcard):
        output = [
            TermColor.bold('Delete flashcard')
        ]
        output.extend(
            flashcard.pformat(
                term_color=TermColor.light_blue
            )
        )
        await self.async_io.print_formatted_output(output)
