import random
import unittest

from unittest import mock
from tempfile import NamedTemporaryFile
from datetime import datetime, timedelta

from config import ConfigAdapter
from run import Play, SpacedRehearsal


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


class TestCaseConfig(unittest.TestCase):

    def setUp(self):
        config_test = """
        [DEFAULT]
        ServerAliveInterval = 45
        Compression = yes
        CompressionLevel = 9
        ForwardX11 = yes

        [bitbucket.org]
        User = hg

        [topsecret.server.com]
        Port = 50022
        ForwardX11 = no
        """
        self.fp = NamedTemporaryFile()
        self.fp.write(config_test.encode('utf-8'))
        self.fp.flush()

    def tearDown(self):
        self.fp.close()

    def test_config_adapter(self):
        config = ConfigAdapter(filename=self.fp.name)
        self.assertEqual(config['bitbucket.org']['User'], 'hg')
        self.assertCountEqual(
            config.sections(),
            ['topsecret.server.com', 'bitbucket.org']
        )
        self.assertTrue(
            config.getboolean('bitbucket.org', 'Compression')
        )
        self.assertEqual(
            config['topsecret.server.com'].get('CompressionLevel'),
            '9'
        )
        self.assertEqual(
            config['topsecret.server.com'].getint('CompressionLevel'),
            9
        )
        self.assertTrue('bitbucket.org' in config)

    def test_config_adapter_singleton(self):
        a_config = ConfigAdapter(filename=self.fp.name)
        a_same_config = ConfigAdapter(self.fp.name)
        self.assertEqual(a_config, a_same_config)

        config_test = """
        [test]
        foo = 45
        """
        with NamedTemporaryFile() as fp:
            fp.write(config_test.encode('utf-8'))
            fp.flush()
            b_config = ConfigAdapter(self.fp.name)
            c_config = ConfigAdapter(filename=fp.name)
            self.assertNotEqual(b_config, c_config)


class TestCaseSpacedRehearsal(unittest.TestCase):

    def setUp(self):
        self.spaced_rehearsal = SpacedRehearsal()

    def test_config(self):
        self.assertEqual(
            self.spaced_rehearsal.config.getint('play', 'answer_timeout'),
            30
        )


if __name__ == '__main__':
    unittest.main()
