import bisect
import random
import sqlite3

from datetime import datetime
from itertools import groupby

from src.flashcard import Flashcard
from src.utils import datetime_utc_now


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
        self.db_conn = sqlite3.connect(database)
        self.db_conn.row_factory = sqlite3.Row
        self.db_cursor = self.db_conn.cursor()
        if setup_db:
            self.setup_users_table()
            self.setup_flashcards_table()
            self.setup_flashcards_history_table()
            self.setup_trigger_update_flashcard_history()

    def __str__(self):
        return '<{0}[conn:{1}]>'.format(
            self.__class__.__name__,
            self.db_conn
        )

    def close(self):
        self.db_cursor.close()
        self.db_conn.close()

    @staticmethod
    def zip_row(row) -> dict:
        return {k: row[k] for k in row.keys()}

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

    def setup_flashcards_history_table(self):
        self.db_cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='flashcards_history';
        """)
        flashcards_history_table = self.db_cursor.fetchone()
        if flashcards_history_table is None:
            with open('sql/flashcards_history.sql') as fh:
                flashcards_history_table = fh.read()
            self.db_cursor.execute(flashcards_history_table)
            self.db_conn.commit()

    def setup_trigger_update_flashcard_history(self):
        self.db_cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='trigger' AND name = 'update_flashcards_history';
        """)
        trigger_update_flashcard_history = self.db_cursor.fetchone()
        if trigger_update_flashcard_history is None:
            with open('sql/trigger_update_flashcard_history.sql') as fh:
                trigger_update_flashcard_history = fh.read()
            self.db_cursor.execute(trigger_update_flashcard_history)
            self.db_conn.commit()

    def get_user(self, login_name):
        self.db_cursor.execute(
            'select * from users where login=?', (login_name,)
        )
        user = self.db_cursor.fetchone()
        if user is not None:
            user = self.zip_row(user)
        return user

    def register_user(self, login_name):
        self.db_cursor.execute(
            'insert into users(login) values (?);',
            (login_name, )
        )
        self.db_conn.commit()

    def count_flashcards(self, user_id, due=None):
        assert isinstance(due, (datetime, type(None)))
        if due is None:
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
                'WHERE user_id = ? AND due <= ?',
                (user_id, due)
            )
        return query.fetchone()['count(*)']

    def get_ready_flashcards(self, user_id):
        query = self.db_cursor.execute(
            'SELECT * '
            'FROM flashcards '
            'WHERE user_id = ? AND due <= ? '
            'ORDER BY due',
            (user_id, datetime_utc_now())
        )
        flashcards = []
        for row in query:
            flashcard = self.zip_row(row=row)
            flashcards.append(flashcard)

        shuffled_flashcards = []
        group_by_date = groupby(
            flashcards,
            key=lambda f: datetime.strptime(
                f['due'][:-6], '%Y-%m-%d %H:%M:%S.%f'
            ).date()
        )
        for date, data in group_by_date:
            flashcards_by_date = list(data)
            random.shuffle(flashcards_by_date)
            shuffled_flashcards.extend(flashcards_by_date)
            
        return shuffled_flashcards

    def add_flashcard(self, flashcard):
        self.db_cursor.execute(
            'insert into flashcards'
            '(user_id, side_a, side_b, box, due, source,'
            ' explanation, examples, phonetic_transcriptions, created, '
            ' retention_origin_date, retention_current_date)'
            'values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
            (flashcard['user_id'], flashcard['side_a'], flashcard['side_b'],
             flashcard['box'], flashcard['due'], flashcard['source'],
             flashcard['explanation'], flashcard['examples'],
             flashcard['phonetic_transcriptions'], datetime_utc_now(),
             flashcard['retention_origin_date'],
             flashcard['retention_current_date'])
        )
        self.db_conn.commit()

    def update_flashcard(
            self, due, box, retention_origin_date, retention_current_date,
            flashcard_id
    ):
        self.db_cursor.execute(
            'update flashcards set due=?, box=?, retention_origin_date=?, '
            'retention_current_date=? where id=?',
            (due, box, retention_origin_date, retention_current_date,
             flashcard_id)
        )
        self.db_conn.commit()

    def get_flashcard_duplicates(self, flashcard: Flashcard):
        query = self.db_cursor.execute(
            'select * from flashcards '
            'where (side_a = ? or side_b = ?) and user_id = ?',
            (flashcard.side_a, flashcard.side_b, flashcard.user_id)
        )
        duplicates = []
        for row in query:
            duplicate = self.zip_row(row=row)
            duplicates.append(duplicate)

        return duplicates

    def get_vis_by_date(self, user_id):
        query = self.db_cursor.execute(
            'SELECT strftime("%Y-%m-%d", due) as key, count(*) as value '
            'FROM flashcards '
            'WHERE user_id = ? '
            'GROUP BY strftime("%Y-%m-%d", due) '
            'ORDER BY strftime("%Y-%m-%d", due);',
            (user_id, )
        )
        data = []
        dates = []
        now = datetime_utc_now().strftime("%Y-%m-%d")
        has_now_as_date = False
        for row in query:
            datum = self.zip_row(row=row)
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
