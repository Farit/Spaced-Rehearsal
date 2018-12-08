from src.mediator.english_mediator import EnglishMediator


def list_mediators():
    return [EnglishMediator.name()]


def get_mediator(name):
    if name == EnglishMediator.name():
        return EnglishMediator()
    raise Exception(f'Mediator with name="{name}" is not found.')
