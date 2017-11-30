import time
import os.path
import random
import string
import sqlite3
import contextlib
import subprocess
import unittest

from unittest import mock
from tempfile import NamedTemporaryFile
from datetime import datetime, timedelta
from itertools import groupby

from utils import datetime_now, datetime_utc_now
from config import ConfigAdapter
from db_session import DBSession
from run import Play, SpacedRehearsal


@unittest.SkipTest
class TestCasePlayFlashcards(unittest.TestCase):

    def setUp(self):
        self.play_flashcard = Play(user_id=1)

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


class TestCaseDBSession(unittest.TestCase):

    def setUp(self):
        self.generated_databases_name = []

    def tearDown(self):
        for gen_database_name in self.generated_databases_name:
            if os.path.exists(gen_database_name):
                subprocess.run(['rm', gen_database_name])

    def _gen_database_name(self):
        name = f'__test_{random.randint(1, 100)}.db'
        while name in self.generated_databases_name:
            name = f'__test_{random.randint(1, 100)}.db'
        self.generated_databases_name.append(name)
        return name

    @staticmethod
    def _gen_random_datetime_before(datetime_str):
        """
        :param datetime_str: '2017-11-10 10:36:25+0300'
        """
        point = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S%z')
        random_timedelta = timedelta(
            days=random.randint(1, 9999),
            seconds=random.randint(0, 3600*24 - 1),
            microseconds=random.randint(0, 1000000 - 1),
            milliseconds=random.randint(0, 1000000),
            minutes=random.randint(1, 60),
            hours=random.randint(1, 23),
            weeks=random.randint(1, 23)
        )
        return point - random_timedelta

    @staticmethod
    def _gen_sequence(size=None):
        population = (
            string.ascii_letters + string.punctuation + string.whitespace
        )
        size = size or random.randint(5, 1000)
        return ''.join(random.choices(population, k=size))

    def _gen_flashcard(self, user_id: int, box: int, due: str):
        assert isinstance(box, int)
        flashcard = {
            'user_id': user_id,
            'side_a': f'side_a_{time.time()}',
            'side_b': f'side_b_{time.time()}',
            'box': box,
            'due': datetime.strptime(due, '%Y-%m-%d %H:%M:%S%z'),
            'source': self._gen_sequence(),
            'explanation': self._gen_sequence(size=5000),
            'examples': self._gen_sequence(size=2000),
            'phonetic_transcriptions': self._gen_sequence(),
        }
        return flashcard

    def test_db_session_signature(self):
        database = self._gen_database_name()
        with self.assertRaises(TypeError):
            DBSession(database, True)

        with contextlib.ExitStack() as stack:
            setup_users_table_mock = stack.enter_context(
                mock.patch.object(DBSession, 'setup_users_table')
            )
            setup_flashcards_table_mock = stack.enter_context(
                mock.patch.object(DBSession, 'setup_flashcards_table')
            )
            setup_flashcards_history_table_mock = stack.enter_context(
                mock.patch.object(DBSession, 'setup_flashcards_history_table')
            )
            setup_trigger_update_flashcard_history_mock = stack.enter_context(
                mock.patch.object(DBSession, 'setup_trigger_update_flashcard_history')
            )
            DBSession(database)
            setup_users_table_mock.assert_not_called()
            setup_flashcards_table_mock.assert_not_called()
            setup_flashcards_history_table_mock.assert_not_called()
            setup_trigger_update_flashcard_history_mock.assert_not_called()

        with contextlib.ExitStack() as stack:
            setup_users_table_mock = stack.enter_context(
                mock.patch.object(DBSession, 'setup_users_table')
            )
            setup_flashcards_table_mock = stack.enter_context(
                mock.patch.object(DBSession, 'setup_flashcards_table')
            )
            setup_flashcards_history_table_mock = stack.enter_context(
                mock.patch.object(DBSession, 'setup_flashcards_history_table')
            )
            setup_trigger_update_flashcard_history_mock = stack.enter_context(
                mock.patch.object(DBSession, 'setup_trigger_update_flashcard_history')
            )
            DBSession(database, setup_db=True)
            setup_users_table_mock.assert_called_once()
            setup_flashcards_table_mock.assert_called_once()
            setup_flashcards_history_table_mock.assert_called_once()
            setup_trigger_update_flashcard_history_mock.assert_called_once()

    def test_db_session_called_with_same_database(self):
        database = self._gen_database_name()
        db_session = DBSession(database)
        same_db_session = DBSession(database)
        self.assertEqual(db_session, same_db_session)

    def test_db_session_called_with_different_database(self):
        db_session = DBSession(self._gen_database_name())
        same_db_session = DBSession(self._gen_database_name())
        self.assertNotEqual(db_session, same_db_session)

    def test_setup_users_table(self):
        database = self._gen_database_name()
        db_session = DBSession(database)
        db_session.setup_users_table()

        db_conn = sqlite3.connect(database)
        db_cursor = db_conn.cursor()
        db_cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='users';
        """)
        self.assertIsNotNone(db_cursor.fetchone())
        db_cursor.close()
        db_conn.close()

        is_exception = False
        try:
            db_session.setup_users_table()
        except Exception:
            is_exception = True

        self.assertFalse(is_exception)

    def test_setup_flashcards_table(self):
        database = self._gen_database_name()
        db_session = DBSession(database)
        db_session.setup_flashcards_table()

        db_conn = sqlite3.connect(database)
        db_cursor = db_conn.cursor()
        db_cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='flashcards';
        """)
        self.assertIsNotNone(db_cursor.fetchone())
        db_cursor.close()
        db_conn.close()

        is_exception = False
        try:
            db_session.setup_flashcards_table()
        except Exception:
            is_exception = True

        self.assertFalse(is_exception)

    def test_setup_flashcards_history_table(self):
        database = self._gen_database_name()
        db_session = DBSession(database)
        db_session.setup_flashcards_history_table()

        db_conn = sqlite3.connect(database)
        db_cursor = db_conn.cursor()
        db_cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='flashcards_history';
        """)
        self.assertIsNotNone(db_cursor.fetchone())
        db_cursor.close()
        db_conn.close()

        is_exception = False
        try:
            db_session.setup_flashcards_history_table()
        except Exception:
            is_exception = True

        self.assertFalse(is_exception)

    def test_setup_trigger_update_flashcard_history(self):
        database = self._gen_database_name()
        db_session = DBSession(database)
        db_session.setup_flashcards_table()
        db_session.setup_trigger_update_flashcard_history()

        db_conn = sqlite3.connect(database)
        db_cursor = db_conn.cursor()
        db_cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='trigger' AND name='update_flashcards_history';
        """)
        self.assertIsNotNone(db_cursor.fetchone())
        db_cursor.close()
        db_conn.close()

        is_exception = False
        try:
            db_session.setup_trigger_update_flashcard_history()
        except Exception:
            is_exception = True

        self.assertFalse(is_exception)

    def test_get_user(self):
        user_login_name = 'user_login_name'
        database = self._gen_database_name()
        db_session = DBSession(database, setup_db=True)
        self.assertIsNone(db_session.get_user(user_login_name))

        db_conn = sqlite3.connect(database)
        db_cursor = db_conn.cursor()
        db_cursor.execute(
            'insert into users (login) values (?)', (user_login_name,)
        )
        db_conn.commit()
        db_cursor.close()
        db_conn.close()

        user = db_session.get_user(user_login_name)
        self.assertIsInstance(user, dict)
        self.assertEqual(user['login'], user_login_name)

    def test_register_user(self):
        user_login_name = 'user_login_name'
        database = self._gen_database_name()
        db_session = DBSession(database, setup_db=True)
        self.assertIsNone(db_session.get_user(user_login_name))

        db_session.register_user(user_login_name)
        user = db_session.get_user(user_login_name)
        self.assertIsInstance(user, dict)
        self.assertEqual(user['login'], user_login_name)

    def test_count_flashcards_total(self):
        user_login_name = 'user_login_name'
        database = self._gen_database_name()
        db_session = DBSession(database, setup_db=True)
        db_session.register_user(user_login_name)
        user = db_session.get_user(user_login_name)

        db_conn = sqlite3.connect(database)
        db_cursor = db_conn.cursor()

        total_number_flashcards = 24
        for i in range(total_number_flashcards):
            flashcard = self._gen_flashcard(
                user_id=user['id'],
                box=0,
                due=datetime_now().strftime('%Y-%m-%d %H:%M:%S%z'),
            )
            db_cursor.execute(
                'insert into flashcards'
                '(user_id, side_a, side_b, box, due, source, '
                'explanation, examples, phonetic_transcriptions)'
                'values (?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (flashcard['user_id'], flashcard['side_a'], flashcard['side_b'],
                 flashcard['box'], flashcard['due'], flashcard['source'],
                 flashcard['explanation'], flashcard['examples'],
                 flashcard['phonetic_transcriptions'])
            )
        db_conn.commit()
        db_cursor.close()
        db_conn.close()

        self.assertEqual(
            db_session.count_flashcards(user['id']),
            total_number_flashcards
        )

    def test_count_flashcards_due(self):
        user_login_name = 'user_login_name'
        database = self._gen_database_name()
        db_session = DBSession(database, setup_db=True)
        db_session.register_user(user_login_name)
        user = db_session.get_user(user_login_name)

        db_conn = sqlite3.connect(database)
        db_cursor = db_conn.cursor()

        data = []
        for _ in range(3000):
            data.append(self._gen_random_datetime_before(
                datetime_now().strftime('%Y-%m-%d %H:%M:%S%z')
            ))
        data.sort()

        group_by_year = groupby(data, lambda d: d.strftime('%Y'))

        for _datetime in data:
            flashcard = self._gen_flashcard(
                user_id=user['id'],
                box=random.randint(1, 100),
                due= _datetime.strftime('%Y-%m-%d %H:%M:%S%z')
            )
            db_cursor.execute(
                'insert into flashcards'
                '(user_id, side_a, side_b, box, due, source, '
                'explanation, examples, phonetic_transcriptions)'
                'values (?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (flashcard['user_id'], flashcard['side_a'],
                 flashcard['side_b'], flashcard['box'], flashcard['due'],
                 flashcard['source'], flashcard['explanation'],
                 flashcard['examples'], flashcard['phonetic_transcriptions'])
            )
        db_conn.commit()
        db_cursor.close()
        db_conn.close()

        total = 0
        for year, data in group_by_year:
            data = list(data)
            total += len(data)
            self.assertEqual(
                db_session.count_flashcards(
                    user_id=user['id'],
                    due=data[-1]
                ),
                total,
            )

    # def test_get_ready_flashcards(self):
    #     user_login_name = 'user_login_name'
    #     database = self._gen_database_name()
    #     db_session = DBSession(database, setup_db=True)
    #     db_session.register_user(user_login_name)
    #     user = db_session.get_user(user_login_name)
    #
    #     db_conn = sqlite3.connect(database)
    #     db_cursor = db_conn.cursor()
    #
    #     data = []
    #     for _ in range(348):
    #         data.append(self._gen_random_datetime_before(
    #             datetime_now().strftime('%Y-%m-%d %H:%M:%S%z')
    #         ))
    #     data.sort()
    #
    #     flashcards = []
    #     for _datetime in data:
    #         flashcard = self._gen_flashcard(
    #             user_id=user['id'],
    #             box=random.randint(1, 100),
    #             due=_datetime.strftime('%Y-%m-%d %H:%M:%S%z')
    #         )
    #         flashcards.append(flashcard)
    #         db_cursor.execute(
    #             'insert into flashcards'
    #             '(user_id, side_a, side_b, box, due, source, '
    #             'explanation, examples, phonetic_transcriptions)'
    #             'values (?, ?, ?, ?, ?, ?, ?, ?, ?);',
    #             (flashcard['user_id'], flashcard['side_a'],
    #              flashcard['side_b'], flashcard['box'], flashcard['due'],
    #              flashcard['source'], flashcard['explanation'],
    #              flashcard['examples'], flashcard['phonetic_transcriptions'])
    #         )
    #     db_conn.commit()
    #     db_cursor.close()
    #     db_conn.close()
    #
    #     ready_flashcards = db_session.get_ready_flashcards(user_id=user['id'])
    #     self.assertEqual(len(ready_flashcards), len(flashcards))
    #     for ind, flashcard in enumerate(flashcards):
    #         ready_flashcard = ready_flashcards[ind]
    #         ready_flashcard.pop('id')
    #         ready_flashcard.pop('created')
    #         ready_flashcard.pop('due')
    #         flashcard.pop('due')
    #         # print(ready_flashcard)
    #         # print(flashcard)
    #         self.assertDictEqual(ready_flashcard, flashcard)

    # def test_trigger_update_flashcard_history(self):
    #     user_login_name = 'user_login_name'
    #     database = self._gen_database_name()
    #     db_session = DBSession(database, setup_db=True)
    #     db_session.register_user(user_login_name)
    #     user = db_session.get_user(user_login_name)
    #
    #     db_conn = sqlite3.connect(database)
    #     db_cursor = db_conn.cursor()
    #     db_cursor.execute(
    #         'insert into flashcards'
    #         '(user_id, side_a, side_b, box, due, source, '
    #         'explanation, examples, phonetic_transcriptions)'
    #         'values (?, ?, ?, ?, ?, ?, ?, ?, ?);',
    #         (user['id'], 'flashcard_side_a', 'flashcard_side_b',
    #          0, datetime.now() + timedelta(days=1), 'flashcard_source',
    #          'flashcard_explanation', 'flashcard_examples',
    #          'flashcard_phonetic_transcriptions')
    #     )
    #     db_conn.commit()
    #     db_cursor.execute(
    #         'update flashcards set due=?, box=? where id=?',
    #         (due, box, flashcard_id)
    #     )
    #     db_conn.commit()
    #     db_cursor.close()
    #     db_conn.close()


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
