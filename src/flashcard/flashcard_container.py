import logging

from typing import Optional, List

from src.flashcard.flashcard import Flashcard


logger = logging.getLogger(__name__)


class FlashcardContainer:

    def __init__(self):
        self._flashcards = {}

    def add(self, flashcard: Flashcard):
        self._flashcards[str(flashcard.flashcard_id)] = flashcard

    def extend(self, flashcards: List[Flashcard]):
        for flashcard in flashcards:
            self.add(flashcard)

    def get(self, flashcard_id) -> Optional[Flashcard]:
        return self._flashcards.get(str(flashcard_id), None)

    def get_ids(self) -> List[str]:
        return [str(fid) for fid in self._flashcards.keys()]

    def __len__(self):
        return len(self._flashcards)

    def __iter__(self):
        return iter(self._flashcards.values())
