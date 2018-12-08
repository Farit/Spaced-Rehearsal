from datetime import timedelta


class FlashcardState:
    def __init__(self, state, answer_difficulty, delay, mem_strength):
        if state not in ['init', 'success', 'failure']:
            raise Exception(f'Unknown state: {state}')

        self.state = state
        self.answer_difficulty = answer_difficulty
        self.delay = delay
        self.mem_strength = mem_strength

    def __repr__(self):
        return (
            f'<{self.state}  answer_difficulty: {self.answer_difficulty} '
            f'delay: {timedelta(hours=self.delay)} '
            f'mem_strength: {self.mem_strength}>'
        )
