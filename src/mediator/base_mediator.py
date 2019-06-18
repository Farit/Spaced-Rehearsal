from datetime import datetime

from src.actions import (
    GeneralReviewAction,
    GeneralCreateAction,
    GeneralAlterAction,
    GeneralSearchAction,
    GeneralDeleteAction
)

from src.flashcard import Flashcard, FlashcardContainer
from src.db_session import DBSession
from src.async_std_io import AsyncStdIO
from src.formatting import Formatting
from src.utils import datetime_now
from src.config import ConfigAdapter


class Mediator:

    def __init__(self):
        self.loop = None
        self.user = None
        self.async_std_io = AsyncStdIO()
        self.formatting = Formatting()
        self.config = ConfigAdapter(filename='config.cfg')
        self.db_session = DBSession(
            self.config['database'].get('name'),
            flashcard_type=self.name(),
            setup_db=True
        )
        self.review_action = self.make_review_action()
        self.create_action = self.make_create_action()
        self.alter_action = self.make_alter_action()
        self.search_action = self.make_search_action()
        self.delete_action = self.make_delete_action()

    @classmethod
    def name(cls):
        raise NotImplemented

    def set_loop(self, loop):
        self.loop = loop
        self.async_std_io.set_loop(loop)

    def make_review_action(self):
        return GeneralReviewAction(mediator=self)

    def make_create_action(self):
        return GeneralCreateAction(mediator=self)

    def make_alter_action(self):
        return GeneralAlterAction(mediator=self)

    def make_search_action(self):
        return GeneralSearchAction(mediator=self)
    
    def make_delete_action(self):
        return GeneralDeleteAction(mediator=self)

    async def launch_review_action(self):
        await self.review_action.launch()

    async def launch_create_action(self):
        await self.create_action.launch()

    async def launch_alter_action(self):
        await self.alter_action.launch()

    async def launch_search_action(self):
        await self.search_action.launch()

    async def launch_delete_action(self):
        await self.delete_action.launch()

    async def exit(self):
        if self.user is not None:
            await self.print(f'Bye {self.user["login"]}!')
        self.db_session.close()

    async def login_user(self, login_name):
        self.user = self.db_session.get_user(login_name)
        return self.user is not None

    async def register_user(self, login_name):
        self.db_session.register_user(login_name)
        await self.print(f'User {login_name} is registered!')

    def get_user_id(self):
        if self.user is not None:
            return self.user['id']

    async def save_flashcard(self, flashcard: Flashcard):
        self.db_session.add_flashcard(flashcard=flashcard)

    async def update_flashcard(self, flashcard: Flashcard):
        self.db_session.update_flashcard(flashcard=flashcard)

    async def update_flashcard_review_state(
            self,
            flashcard_id: int,
            current_review_timestamp: datetime,
            current_result: str,
            next_review_timestamp: datetime,
            next_review_version: int,
    ) -> None:
        self.db_session.update_flashcard_review_state(
            flashcard_id=flashcard_id,
            current_result=current_result,
            current_review_timestamp=current_review_timestamp,
            next_review_timestamp=next_review_timestamp,
            next_review_version=next_review_version,
        )

    async def delete_flashcard(self, flashcard: Flashcard):
        self.db_session.delete_flashcard(flashcard=flashcard)

    async def search_flashcard(self, *search_queries):
        flashcards = self.db_session.search(
            *search_queries,
            user_id=self.get_user_id()
        )
        return flashcards

    async def get_flashcards(self):
        return self.db_session.get_flashcards(user_id=self.get_user_id())

    async def launch_search(self):
        result = await self.search_action.launch_search()
        return result

    async def count_total_flashcards(self):
        total_number = self.db_session.count_flashcards(
            user_id=self.get_user_id()
        )
        return total_number

    async def count_review_flashcards(self):
        review_number = self.db_session.count_flashcards(
            user_id=self.get_user_id(),
            review_timestamp=datetime_now()
        )
        return review_number

    async def get_prev_review_timestamp(self, flashcard):
        previous_review_timestamp = self.db_session.get_prev_review_timestamp(
            flashcard=flashcard
        )
        return previous_review_timestamp

    async def get_ready_flashcards(self) -> FlashcardContainer:
        flashcard_container: FlashcardContainer = (
            self.db_session.get_ready_flashcards(
                user_id=self.get_user_id()
            )
        )
        return flashcard_container

    async def print_flashcard(
        self,
        flashcard: Flashcard,
        include_fields=None,
        exclude_fields=None,
        colour_func=None,
        bottom_margin=None
    ):
        if exclude_fields is not None and include_fields is not None:
            raise Exception(
                'You can not specify both exclude_fields and include_fields'
            )

        if exclude_fields is not None:
            fields = list(set(flashcard.printable_fields) - set(exclude_fields))
        elif include_fields is not None:
            fields = include_fields
        else:
            fields = None

        for key, value in flashcard.print_format(fields=fields):
            if colour_func is not None:
                key = colour_func(key)
            data = f'{key}: {value}'
            await self.async_std_io.print(data)

        if bottom_margin is not None:
            await self.async_std_io.print(*['']*bottom_margin)

    async def print(
        self,
        *msgs,
        red: bool=False,
        yellow: bool=False,
        blue: bool=False,
        light_blue: bool=False,
        purple: bool=False,
        green: bool=False,
        grey: bool=False,
        bold: bool=False,
        underline: bool=False,
        bottom_margin: int=None
    ):
        bottom_margin = bottom_margin or 0

        if red:
            msgs = [self.format_red(msg) for msg in msgs]
        if grey:
            msgs = [self.format_grey(msg) for msg in msgs]
        if green:
            msgs = [self.format_green(msg) for msg in msgs]
        if yellow:
            msgs = [self.format_yellow(msg) for msg in msgs]
        if purple:
            msgs = [self.format_purple(msg) for msg in msgs]
        if blue:
            msgs = [self.format_blue(msg) for msg in msgs]
        if light_blue:
            msgs = [self.format_light_blue(msg) for msg in msgs]
        if bold:
            msgs = [self.format_bold(msg) for msg in msgs]
        if underline:
            msgs = [self.format_underline(msg) for msg in msgs]
        
        msgs = [*msgs, *['']*bottom_margin]
        await self.async_std_io.print(*msgs)

    def format_green(self, msg: str) -> str:
        return self.formatting.green(msg)

    def format_yellow(self, msg: str) -> str:
        return self.formatting.yellow(msg)

    def format_red(self, msg: str) -> str:
        return self.formatting.red(msg)

    def format_blue(self, msg: str) -> str:
        return self.formatting.blue(msg)

    def format_light_blue(self, msg: str) -> str:
        return self.formatting.light_blue(msg)

    def format_purple(self, msg: str) -> str:
        return self.formatting.purple(msg)

    def format_grey(self, msg: str) -> str:
        return self.formatting.grey(msg)

    def format_bold(self, msg: str) -> str:
        return self.formatting.bold(msg)

    def format_underline(self, msg: str) -> str:
        return self.formatting.underline(msg)

    async def input_confirmation(self, *msgs):
        action = await self.async_std_io.input_action(
            action_answers=('y', 'n'),
            action_msgs=[
                *msgs,
                f'[{self.format_green("y")}/{self.format_red("n")}]',
            ]
        )
        return action == 'y'

    async def input_action(self, action_answers, action_msgs):
        action = await self.async_std_io.input_action(
            action_answers=action_answers, 
            action_msgs=action_msgs
        )
        return action

    async def input(self, msg, pre_fill=None, history=None):
        data = await self.async_std_io.input(
            msg, pre_fill=pre_fill, history=history
        )
        return data

    async def input_question(self, pre_fill: str=None):
        question = await self.input(
            'Question', pre_fill=pre_fill
        )
        return question

    async def input_answer(self, pre_fill: str=None):
        answer = await self.input(
            'Answer', pre_fill=pre_fill
        )
        return answer

    async def input_source(self, pre_fill: str=None):
        source_tags = self.db_session.get_source_tags(
            user_id=self.get_user_id()
        )
        source = await self.input(
            'Source',
            pre_fill=(
                pre_fill or (source_tags[0] if source_tags else '')
            ),
            history=source_tags
        )
        return source
