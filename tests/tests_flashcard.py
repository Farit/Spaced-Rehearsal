import time
import string
import random
import unittest

from datetime import timedelta, datetime

from src.utils import datetime_utc_now
from src.flashcard import Flashcard


class TestCaseFlashcard(unittest.TestCase):

    @staticmethod
    def _gen_sequence(size=None):
        population = (
            string.ascii_letters + string.punctuation + string.whitespace
        )
        size = size or random.randint(5, 1000)
        return ''.join(random.choices(population, k=size))

    def test_empty(self):
        user_id = 1
        flashcard = Flashcard(user_id=user_id)
        self.assertEqual(flashcard.user_id, user_id)
        self.assertIsNone(flashcard.id)
        self.assertIsNone(flashcard.side_a)
        self.assertIsNone(flashcard.side_b)
        self.assertIsNone(flashcard.source)
        self.assertIsNone(flashcard.phonetic_transcriptions)
        self.assertIsNone(flashcard.explanation)
        self.assertIsNone(flashcard.examples)
        self.assertEqual(flashcard.box, 0)
        self.assertIsNone(flashcard.due)
        self.assertIsNone(flashcard.created)

    def test_side_a(self):
        user_id = 1
        flashcard = Flashcard(user_id=user_id)

        side_a = ' Где      находится автовокзал     ?     '
        flashcard.side_a = side_a
        self.assertEqual(flashcard.side_a, 'Где находится автовокзал?')

        side_a = ' Доброе      утро ,  мир     !     '
        flashcard.side_a = side_a
        self.assertEqual(flashcard.side_a, 'Доброе утро, мир!')

        side_a = 3
        with self.assertRaises(TypeError) as cm:
            flashcard.side_a = side_a
        self.assertEqual(
            str(cm.exception), f'side_a: {side_a!r} must be str or None'
        )

    def test_side_b(self):
        user_id = 1
        flashcard = Flashcard(user_id=user_id)

        side_b = ' Where   is    the bus   station   ?     '
        flashcard.side_b = side_b
        self.assertEqual(flashcard.side_b, 'Where is the bus station?')

        side_b = ' Good    morning      ,    world   !'
        flashcard.side_b = side_b
        self.assertEqual(flashcard.side_b, 'Good morning, world!')

        side_b = 3
        with self.assertRaises(TypeError) as cm:
            flashcard.side_b = side_b
        self.assertEqual(
            str(cm.exception), f'side_b: {side_b!r} must be str or None'
        )

    def test_source(self):
        user_id = 1
        flashcard = Flashcard(user_id=user_id)
        self.assertIsNone(flashcard.source)

        source = 'Woe is I Jr.'
        flashcard.source = source
        self.assertEqual(flashcard.source, source)

        user_id = 2
        new_flashcard = Flashcard(user_id=user_id)
        new_source = '\p'
        new_flashcard.source = new_source
        self.assertEqual(new_flashcard.source, new_source)

        user_id = 3
        another_new_flashcard = Flashcard(user_id=user_id)
        self.assertIsNone(another_new_flashcard.source)

        source = 32
        with self.assertRaises(TypeError) as cm:
            flashcard.source = source
        self.assertEqual(
            str(cm.exception), f'source: {source!r} must be str or None'
        )

    def test_phonetic_transcriptions(self):
        user_id = 1
        flashcard = Flashcard(user_id=user_id)

        phonetic_transcriptions = 'behave |bɪˈheɪv|'
        flashcard.phonetic_transcriptions = phonetic_transcriptions
        self.assertEqual(
            flashcard.phonetic_transcriptions, phonetic_transcriptions
        )

        phonetic_transcriptions = 32
        with self.assertRaises(TypeError) as cm:
            flashcard.phonetic_transcriptions = phonetic_transcriptions
        self.assertEqual(
            str(cm.exception),
            f'phonetic_transcriptions: {phonetic_transcriptions!r} '
            f'must be str or None'
        )

    def test_explanation(self):
        user_id = 1
        flashcard = Flashcard(user_id=user_id)

        explanation = (
            'act or conduct oneself in a specified way, '
            'especially towards others'
        )
        flashcard.explanation = explanation
        self.assertEqual(flashcard.explanation, explanation)

        explanation = 32
        with self.assertRaises(TypeError) as cm:
            flashcard.explanation = explanation
        self.assertEqual(
            str(cm.exception),
            f'explanation: {explanation!r} must be str or None'
        )

    def test_examples(self):
        user_id = 1
        flashcard = Flashcard(user_id=user_id)

        examples = 'he always behaved like a gentleman'
        flashcard.examples = examples
        self.assertEqual(flashcard.examples, examples)

        examples = 32
        with self.assertRaises(TypeError) as cm:
            flashcard.examples = examples
        self.assertEqual(
            str(cm.exception),
            f'examples: {examples!r} must be str or None'
        )

    def test_box(self):
        user_id = 1
        flashcard = Flashcard(user_id=user_id)

        box = 2
        flashcard.box = box
        self.assertEqual(flashcard.box, box)

        box = '8'
        with self.assertRaises(TypeError) as cm:
            flashcard.box = box
        self.assertEqual(str(cm.exception), f'box: {box!r} must be int')

    def test_due(self):
        user_id = 1
        flashcard = Flashcard(user_id=user_id)

        due = datetime_utc_now() + timedelta(days=2**1)
        flashcard.due = due
        self.assertEqual(flashcard.due, due)

        due = 67
        with self.assertRaises(TypeError) as cm:
            flashcard.due = due
        self.assertEqual(
            str(cm.exception), f'due: {due!r} must be datetime or None'
        )

    def test_getitem(self):
        data = {
            'user_id': 5,
            'side_a': f'side_a_{time.time()}',
            'side_b': f'side_b_{time.time()}',
            'box': 5,
            'due': datetime.strptime(
                '2017-11-10 10:36:25+0300', '%Y-%m-%d %H:%M:%S%z'
            ),
            'source': self._gen_sequence(),
            'explanation': self._gen_sequence(size=5000),
            'examples': self._gen_sequence(size=2000),
            'phonetic_transcriptions': self._gen_sequence(),
        }
        flashcard = Flashcard(**data)

        self.assertEqual(flashcard.user_id, data['user_id'])
        self.assertEqual(flashcard['user_id'], data['user_id'])

        self.assertEqual(flashcard.side_a, data['side_a'])
        self.assertEqual(flashcard['side_a'], data['side_a'])

        self.assertEqual(flashcard.side_b, data['side_b'])
        self.assertEqual(flashcard['side_b'], data['side_b'])

        self.assertEqual(flashcard.box, data['box'])
        self.assertEqual(flashcard['box'], data['box'])

        self.assertEqual(flashcard.due, data['due'])
        self.assertEqual(flashcard['due'], data['due'])

        self.assertEqual(flashcard.source, data['source'])
        self.assertEqual(flashcard['source'], data['source'])

        self.assertEqual(flashcard.explanation, data['explanation'])
        self.assertEqual(flashcard['explanation'], data['explanation'])

        self.assertEqual(flashcard.examples, data['examples'])
        self.assertEqual(flashcard['examples'], data['examples'])

        self.assertEqual(
            flashcard.phonetic_transcriptions,
            data['phonetic_transcriptions']
        )
        self.assertEqual(
            flashcard['phonetic_transcriptions'],
            data['phonetic_transcriptions']
        )

    def test_str(self):
        user_id = 1
        flashcard = Flashcard(user_id=user_id)
        side_a = 'Привет'
        flashcard.side_a = side_a
        side_b = 'Hello'
        flashcard.side_b = side_b
        self.assertEqual(str(flashcard), f'[{side_a}] / [{side_b}]')
        self.assertEqual(f'{flashcard}', f'[{side_a}] / [{side_b}]')


if __name__ == '__main__':
    unittest.main()
