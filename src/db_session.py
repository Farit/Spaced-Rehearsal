import bisect
import random
import sqlite3

from datetime import datetime
from itertools import groupby
from typing import List

from src.flashcard import Flashcard
from src.scheduler import FlashcardState
from src.utils import (
    datetime_now, datetime_change_timezone,
    convert_datetime_to_local
)


class DBSession:
    """
    Behaves as Singleton when called with the same database.
    """

    def __new__(cls, database, **kwargs):
        if not hasattr(cls, '_instances'):
            setattr(cls, '_instances', {})

        if database not in getattr(cls, '_instances'):
            # Call super to eliminate infinite recursion
            # You must not pass args and kwargs, because base class 'object'
            # takes only one argument, class object which instance must be
            # created. According to __new__ method specification, it must return
            # empty instance of the class. Actual instance initialization
            # call takes place in metaclass __call__ method.
            _instance = super().__new__(cls)
            getattr(cls, '_instances')[database] = _instance

        return getattr(cls, '_instances')[database]

    def __init__(self, database, *, setup_db=False):
        self.register_flashcard_state_adapter()
        self.db_conn = sqlite3.connect(
            database, detect_types=sqlite3.PARSE_DECLTYPES
        )
        self.db_conn.row_factory = sqlite3.Row
        self.db_cursor = self.db_conn.cursor()
        if setup_db:
            self.setup_users_table()
            self.setup_flashcards_table()
            self.setup_flashcard_states_table()
            self.setup_trigger_log_update_flashcard_state()
            self.setup_trigger_log_insert_flashcard_state()
            self.setup_full_text_search()

    def __str__(self):
        return '<{0}[conn:{1}]>'.format(
            self.__class__.__name__,
            self.db_conn
        )

    def close(self):
        self.db_cursor.close()
        self.db_conn.close()

    @staticmethod
    def register_flashcard_state_adapter():
        def adapt_flashcard_state(flashcard_state: FlashcardState):
            return (
                f"{flashcard_state.state};"
                f"{flashcard_state.answer_difficulty};"
                f"{flashcard_state.delay};"
                f"{flashcard_state.mem_strength}"
            )
        sqlite3.register_adapter(FlashcardState, adapt_flashcard_state)

    def setup_users_table(self):
        self.db_cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='users';
        """)
        users_table = self.db_cursor.fetchone()
        if users_table is None:
            with open('sql/users.sql') as fh:
                users_table = fh.read()
            self.db_cursor.execute(users_table)
            self.db_conn.commit()

    def setup_flashcards_table(self):
        self.db_cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='flashcards';
        """)
        flashcards_table = self.db_cursor.fetchone()
        if flashcards_table is None:
            with open('sql/flashcards.sql') as fh:
                flashcards_table = fh.read()
            self.db_cursor.execute(flashcards_table)
            self.db_conn.commit()

    def setup_flashcard_states_table(self):
        self.db_cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='flashcard_states';
        """)
        flashcard_states_table = self.db_cursor.fetchone()
        if flashcard_states_table is None:
            with open('sql/flashcard_states.sql') as fh:
                flashcard_states_table = fh.read()
            self.db_cursor.execute(flashcard_states_table)
            self.db_conn.commit()

    def setup_trigger_log_update_flashcard_state(self):
        self.db_cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='trigger' AND name = 'log_update_flashcard_state';
        """)
        trigger_log_update_flashcard_state = self.db_cursor.fetchone()
        if trigger_log_update_flashcard_state is None:
            with open('sql/trigger_log_update_flashcard_state.sql') as fh:
                trigger_log_update_flashcard_state = fh.read()
            self.db_cursor.execute(trigger_log_update_flashcard_state)
            self.db_conn.commit()

    def setup_trigger_log_insert_flashcard_state(self):
        self.db_cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='trigger' AND name = 'log_insert_flashcard_state';
        """)
        trigger_log_insert_flashcard_state = self.db_cursor.fetchone()
        if trigger_log_insert_flashcard_state is None:
            with open('sql/trigger_log_insert_flashcard_state.sql') as fh:
                trigger_log_insert_flashcard_state = fh.read()
            self.db_cursor.execute(trigger_log_insert_flashcard_state)
            self.db_conn.commit()

    def setup_full_text_search(self):
        self.db_cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='fts_flashcards';
        """)
        fts_flashcards_virtual_table = self.db_cursor.fetchone()
        if fts_flashcards_virtual_table is None:
            with open('sql/fts_flashcards.sql') as fh:
                fts_flashcards_virtual_table = fh.read()
            self.db_cursor.executescript(fts_flashcards_virtual_table)
            self.db_conn.commit()

    def get_user(self, login_name):
        self.db_cursor.execute(
            'select * from users where login=?', (login_name,)
        )
        user = self.db_cursor.fetchone()
        return user

    def register_user(self, login_name) -> None:
        with self.db_conn:
            self.db_cursor.execute(
                'insert into users(login) values (?);',
                (login_name, )
            )

    def count_flashcards(self, user_id, review_timestamp=None) -> int:
        """
        :param user_id: User identifier
        :param review_timestamp: Timestamp with a localtime zone.
        :return: Number of flashcards.
        """
        assert isinstance(review_timestamp, (datetime, type(None)))
        if review_timestamp is None:
            query = self.db_cursor.execute(
                'SELECT count(*) '
                'FROM flashcards '
                'WHERE user_id = ?',
                (user_id,)
            )
        else:
            query = self.db_cursor.execute(
                'SELECT count(*) '
                'FROM flashcards '
                'WHERE user_id = ? AND '
                'datetime(review_timestamp, "localtime") <= ?',
                (user_id, review_timestamp)
            )
        return query.fetchone()['count(*)']

    def get_ready_flashcards(self, user_id: int) -> List[Flashcard]:
        query = self.db_cursor.execute(
            'SELECT '
            'id as flashcard_id, user_id, side_question, side_answer, '
            'review_timestamp, source, explanation, examples, '
            'phonetic_transcriptions, created, state '
            'FROM flashcards '
            'WHERE user_id = ? AND '
            'datetime(review_timestamp, "localtime") <= ? '
            'ORDER BY datetime(review_timestamp, "localtime")',
            (user_id, datetime_now())
        )
        flashcards = []
        for row in query:
            flashcard = dict(row)
            flashcard['review_timestamp'] = convert_datetime_to_local(
                row['review_timestamp']
            )
            flashcard['created'] = convert_datetime_to_local(
                row['created']
            )
            flashcards.append(Flashcard(**flashcard))

        shuffled_flashcards = []
        group_by_date = groupby(
            flashcards,
            key=lambda f: f['review_timestamp'].date()
        )
        for date, data in group_by_date:
            flashcards_by_date = list(data)
            random.shuffle(flashcards_by_date)
            shuffled_flashcards.extend(flashcards_by_date)
            
        return shuffled_flashcards

    def add_flashcard(self, flashcard: Flashcard) -> None:
        with self.db_conn:
            data = dict(flashcard)

            # Convert timestamps to UTC.
            data['review_timestamp'] = datetime_change_timezone(
                data['review_timestamp'], offset=0
            )
            data['created'] = datetime_change_timezone(
                data['created'], offset=0
            )

            self.db_cursor.execute(
                'INSERT INTO flashcards'
                '(user_id, side_question, side_answer, review_timestamp,'
                'source, explanation, examples, phonetic_transcriptions, '
                'created, state) '
                'VALUES (:user_id, :side_question, :side_answer, '
                ':review_timestamp, :source, :explanation, :examples, '
                ':phonetic_transcriptions, :created, :state) ',
                data
            )

    def update_flashcard_state(self, flashcard: Flashcard) -> None:
        with self.db_conn:
            self.db_cursor.execute(
                'UPDATE flashcards '
                'SET review_timestamp=:review_timestamp, state=:state '
                'WHERE id=:flashcard_id',
                {
                    'flashcard_id': flashcard.flashcard_id,
                    'review_timestamp': datetime_change_timezone(
                        flashcard.review_timestamp, offset=0
                    ),
                    'state': flashcard.state
                }
            )

    def get_flashcard_duplicates(self, flashcard: Flashcard) -> List[Flashcard]:
        duplicates = []
        if flashcard.side_answer or flashcard.side_question:

            if flashcard.side_answer and flashcard.side_question:
                needle = (
                    f"'{flashcard.side_answer} OR {flashcard.side_question}'"
                )
            elif flashcard.side_question:
                needle = f"'{flashcard.side_question}'"
            else:
                needle = f"'{flashcard.side_answer}'"

            query = self.db_cursor.execute(
                "select docid "
                "from fts_flashcards "
                "where fts_flashcards match ?",
                (needle, )
            )
            duplicate_ids = tuple(row['docid'] for row in query)

            if duplicate_ids:
                if len(duplicate_ids) == 1:
                    duplicate_ids = f'({duplicate_ids[0]})'
                else:
                    duplicate_ids = str(duplicate_ids)

                query = (
                    f'select '
                    f'id as flashcard_id, user_id, side_question, side_answer, '
                    f'review_timestamp, source, explanation, examples, '
                    f'phonetic_transcriptions, created, state '
                    f'from flashcards '
                    f'where id in {duplicate_ids} and '
                    f'user_id = {flashcard.user_id}'
                )
                query = self.db_cursor.execute(query)
                for row in query:
                    flashcard = dict(row)
                    flashcard['review_timestamp'] = convert_datetime_to_local(
                        row['review_timestamp']
                    )
                    flashcard['created'] = convert_datetime_to_local(
                        row['created']
                    )
                    duplicates.append(Flashcard(**flashcard))

        return duplicates

    def get_vis_by_date(self, user_id):
        query = self.db_cursor.execute(
            'SELECT strftime("%Y-%m-%d", review_timestamp, "localtime") as key,'
            ' count(*) as value '
            'FROM flashcards '
            'WHERE user_id = ? '
            'GROUP BY strftime("%Y-%m-%d", review_timestamp, "localtime") '
            'ORDER BY strftime("%Y-%m-%d", review_timestamp, "localtime");',
            (user_id, )
        )
        data = []
        dates = []
        now = datetime_now().strftime("%Y-%m-%d")
        has_now_as_date = False
        for row in query:
            datum = {key: row[key] for key in row.keys()}
            date = datum['key']
            if date == now:
                has_now_as_date = True
            dates.append(date)
            data.append(datum)

        if not has_now_as_date:
            if not data:
                data.append({'key': now, 'value': 0})
            else:
                data.insert(
                    bisect.bisect_left(dates, now),
                    {'key': now, 'value': 0}
                )
        return data
