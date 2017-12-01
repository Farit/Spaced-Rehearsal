import unittest


from utils import normalize_value


class TestCaseFlashcard(unittest.TestCase):

    def test_normalize_value(self):
        self.assertEqual(
            normalize_value('  Good    morning  ,  world    !'),
            'Good morning, world!'
        )
        self.assertEqual(
            normalize_value('  Do    not  worry   .'),
            'Do not worry.'
        )
        self.assertEqual(
            normalize_value('  Do    not  worry   .', remove_trailing='.'),
            'Do not worry'
        )
        self.assertEqual(
            normalize_value(
                '  Do    not  worry   .', remove_trailing='.', to_lower=True
            ),
            'do not worry'
        )
        self.assertEqual(
            normalize_value('  Hello   ?   !  '),
            'Hello?!'
        )
        self.assertEqual(
            normalize_value('  HELLO,  WORLD   ?   !  ', to_lower=True),
            'hello, world?!'
        )
        self.assertEqual(
            normalize_value('  Hello   ?   !  ', remove_trailing='?!'),
            'Hello'
        )
        with self.assertRaises(TypeError):
            normalize_value(' HELLO, ! ', '!', to_lower=True),


if __name__ == '__main__':
    unittest.main()