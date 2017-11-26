import random
import unittest

from unittest import mock
from datetime import datetime, timedelta

from run import Play


class TestCasePlayFlashcards(unittest.TestCase):

    def setUp(self):
        self.play_flashcard = Play(db_conn=None, db_cursor=None)

    def test_save_result(self):
        self._test_save_result(
            entered_side_b='true',
            flashcard_side_b='true',
            is_timeout=False,
            flashcard_box=3,
            expected_box=4
        )
        self._test_save_result(
            entered_side_b='true',
            flashcard_side_b='true',
            is_timeout=True,
            flashcard_box=5,
            expected_box=0
        )
        self._test_save_result(
            entered_side_b='true',
            flashcard_side_b='false',
            is_timeout=False,
            flashcard_box=2,
            expected_box=0
        )
        self._test_save_result(
            entered_side_b='true',
            flashcard_side_b='false',
            is_timeout=True,
            flashcard_box=1,
            expected_box=0
        )

    def _test_save_result(
            self,
            entered_side_b: str,
            flashcard_side_b: str,
            flashcard_box: int,
            is_timeout: bool,
            expected_box: int
    ):
        flashcard = {'id': random.randint(1, 100), 'box': flashcard_box}
        expected_due = datetime.now() + timedelta(days=2**expected_box)

        self.play_flashcard.save_result = mock.MagicMock()
        self.play_flashcard.handle_answer(
            flashcard, entered_side_b, flashcard_side_b, is_timeout
        )
        self.play_flashcard.save_result.assert_called_once()
        call_args = self.play_flashcard.save_result.call_args

        self.assertEqual(call_args[0][1], expected_box)
        self.assertEqual(call_args[0][2], flashcard['id'])
        self.assertEqual(call_args[0][0].date(), expected_due.date())


if __name__ == '__main__':
    unittest.main()
