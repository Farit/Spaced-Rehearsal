from config import ConfigAdapter
from utils import TermColor, Communication


class BaseClass:

    def __init__(self):
        self.config = ConfigAdapter(filename='config.cfg')

    @staticmethod
    def request_input(request_msgs, request_answers):
        assert isinstance(request_answers, tuple), \
            f'request answers must be tuple'
        assert isinstance(request_msgs, list), f'request msg must be list'

        action = None
        while action not in request_answers:
            for msg in request_msgs:
                Communication.print_output(*msg)
            if action is not None:
                Communication.print_output(
                    TermColor.red(f'Invalid command: {action}')
                )
            action = Communication.print_action()
            action = action.strip()
        return action
