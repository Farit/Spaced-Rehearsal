from src.flashcard import Flashcard


class TextToSpeech:

    def __init__(self, flashcard: Flashcard):
        self.flashcard = flashcard

    def synthesize_audio(self):
        return None
