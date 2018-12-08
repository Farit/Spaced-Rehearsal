from abc import ABC, abstractmethod


class AbstractBaseAction(ABC):

    def __init__(self, mediator):
        self.mediator = mediator

    @property
    @abstractmethod
    def action_name(self):
        pass

    async def launch(self):
        await self.mediator.print(
            f'{self.action_name.lower().capitalize()} Flashcard',
            bold=True
        )
        await self.mediator.print(
            f'Pressing {self.mediator.format_red("Ctrl+D")} '
            f'terminates action.',
            bottom_margin=1
        )
