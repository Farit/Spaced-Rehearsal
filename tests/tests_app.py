import unittest

from src.app import SpacedRehearsal


class TestCaseApp(unittest.TestCase):

    def setUp(self):
        self.spaced_rehearsal = SpacedRehearsal()

    def test_config(self):
        self.assertEqual(
            self.spaced_rehearsal.config.getint('play', 'answer_timeout'),
            30
        )


if __name__ == '__main__':
    unittest.main()
