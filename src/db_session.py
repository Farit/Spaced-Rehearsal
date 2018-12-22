import re
import bisect
import random
import sqlite3
import logging

from datetime import datetime
from itertools import groupby
from typing import List

from src.flashcard import Flashcard, FlashcardContainer, FlashcardState
from src.utils import (
    datetime_now,
    datetime_change_timezone,
    convert_datetime_to_local,
    normalize_value
)

logger = logging.getLogger(__name__)


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
            self.setup_flashcard_example_table()
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

    def setup_flashcard_example_table(self):
        self.db_cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='flashcard_example';
        """)
        flashcard_example_table = self.db_cursor.fetchone()
        if flashcard_example_table is None:
            with open('sql/flashcard_example.sql') as fh:
                flashcard_example_table = fh.read()
            self.db_cursor.execute(flashcard_example_table)
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

    def _get_flashcards(
            self, request: str, request_params: dict=None
    ) -> List[Flashcard]:

        request_params = request_params or {}
        query = self.db_cursor.execute(
            f'SELECT '
            f'    id as flashcard_id, '
            f'    user_id, '
            f'    side_question, '
            f'    side_answer, '
            f'    review_timestamp, '
            f'    source, '
            f'    explanation, '
            f'    phonetic_transcriptions, '
            f'    created, '
            f'    state '
            f'FROM flashcards '
            f'{request}',
            request_params
        )
        flashcards = []
        for row in query:
            data = dict(row)
            examples = self.db_cursor.execute(
                'SELECT example '
                'FROM flashcard_example '
                'WHERE flashcard_id = :flashcard_id',
                {'flashcard_id': data['flashcard_id']}
            )
            data['examples'] = [r['example'] for r in examples]

            state_match = re.match(
                r'''
                    ^(?P<state>.+);
                    (?P<answer_difficulty>.+);
                    (?P<delay>.+);
                    (?P<mem_strength>.+)$
                ''',
                data['state'],
                flags=re.VERBOSE
            )
            state = state_match.group('state')
            answer_difficulty = float(state_match.group('answer_difficulty'))
            delay = int(state_match.group('delay'))
            mem_strength = state_match.group('mem_strength')
            mem_strength = (
                int(mem_strength) if mem_strength != 'None' else None
            )
            flashcard = Flashcard(
                user_id=data['user_id'],
                question=data['side_question'],
                answer=data['side_answer'],
                created=convert_datetime_to_local(data['created']),
                state=FlashcardState(
                    state=state, answer_difficulty=answer_difficulty,
                    delay=delay, mem_strength=mem_strength
                ),
                review_timestamp=convert_datetime_to_local(
                    data['review_timestamp']
                ),
                flashcard_id=data['flashcard_id'],
                phonetic_transcription=data['phonetic_transcriptions'],
                source=data['source'],
                explanation=data['explanation'],
                examples=data['examples']
            )
            flashcards.append(flashcard)

        return flashcards

    def get_ready_flashcards(self, user_id: int) -> FlashcardContainer:
        flashcards = self._get_flashcards(
            request=(
                f'WHERE user_id = :user_id AND '
                f'datetime(review_timestamp, "localtime") <= :now '
                f'ORDER BY datetime(review_timestamp, "localtime")'
            ),
            request_params={
                'user_id': user_id,
                'now': datetime_now()
            }
        )

        flashcard_container = FlashcardContainer()
        group_by_date = groupby(
            flashcards,
            key=lambda f: f['review_timestamp'].date()
        )
        for date, data in group_by_date:
            flashcards_by_date = list(data)
            random.shuffle(flashcards_by_date)
            flashcard_container.extend(flashcards_by_date)

        return flashcard_container

    def add_flashcard(self, flashcard: Flashcard) -> None:
        with self.db_conn:
            self.db_cursor.execute(
                'INSERT INTO flashcards('
                '    user_id, '
                '    side_question, '
                '    side_answer, '
                '    review_timestamp, '
                '    source, '
                '    explanation, '
                '    phonetic_transcriptions, '
                '    created, '
                '    state'
                ') '
                'VALUES ('
                '    :user_id, '
                '    :question, '
                '    :answer, '
                '    :review_timestamp, '
                '    :source, '
                '    :explanation, '
                '    :phonetic_transcriptions, '
                '    :created, '
                '    :state'
                ') ',
                {
                    'user_id': flashcard.user_id,
                    'question': flashcard.question,
                    'answer': flashcard.answer,
                    'review_timestamp': datetime_change_timezone(
                        flashcard.review_timestamp, offset=0
                    ),
                    'source': flashcard.source,
                    'explanation': flashcard.explanation,
                    'phonetic_transcriptions': flashcard.phonetic_transcription,
                    'created': datetime_change_timezone(
                        flashcard.created, offset=0
                    ),
                    'state': flashcard.state,
                }
            )
            flashcard.flashcard_id = self.db_cursor.lastrowid

            for example in flashcard.examples:
                self.db_cursor.execute(
                    'INSERT INTO flashcard_example(flashcard_id, example)'
                    'VALUES (:flashcard_id, :example)',
                    {
                        'flashcard_id': flashcard.id,
                        'example': example
                    }
                )

    def update_flashcard(self, flashcard: Flashcard) -> None:
        with self.db_conn:
            self.db_cursor.execute(
                'UPDATE flashcards SET '
                '   side_question=:question, '
                '   side_answer=:answer, '
                '   source=:source, '
                '   explanation=:explanation, '
                '   phonetic_transcriptions=:phonetic_transcriptions '
                'WHERE id=:flashcard_id',
                {
                    'flashcard_id': flashcard.flashcard_id,
                    'question': flashcard.question,
                    'answer': flashcard.answer,
                    'source': flashcard.source,
                    'explanation': flashcard.explanation,
                    'phonetic_transcriptions': flashcard.phonetic_transcription
                }
            )
            self.db_cursor.execute(
                'DELETE FROM flashcard_example '
                'WHERE flashcard_id=:flashcard_id',
                {
                    'flashcard_id': flashcard.flashcard_id
                }
            )
            for example in flashcard.examples:
                self.db_cursor.execute(
                    'INSERT INTO flashcard_example(flashcard_id, example)'
                    'VALUES (:flashcard_id, :example)',
                    {
                        'flashcard_id': flashcard.id,
                        'example': example
                    }
                )

    def delete_flashcard(self, flashcard: Flashcard) -> None:
        with self.db_conn:
            self.db_cursor.executescript(f"""
                DELETE FROM flashcard_states 
                WHERE flashcard_id={flashcard.flashcard_id};
                DELETE FROM flashcard_example
                WHERE flashcard_id={flashcard.flashcard_id};
                DELETE FROM flashcards
                WHERE id={flashcard.flashcard_id};
            """)

    def update_flashcard_state(self, flashcard: Flashcard) -> None:
        with self.db_conn:
            self.db_cursor.execute(
                'UPDATE flashcards SET '
                '   review_timestamp=:review_timestamp, '
                '   state=:state '
                'WHERE id=:flashcard_id',
                {
                    'flashcard_id': flashcard.flashcard_id,
                    'review_timestamp': datetime_change_timezone(
                        flashcard.review_timestamp, offset=0
                    ),
                    'state': flashcard.state
                }
            )

    def search(self, *search_queries, user_id) -> FlashcardContainer:
        flashcard_container = FlashcardContainer()

        search_queries = [
            s.strip().lower() for s in search_queries if s.strip()
        ]
        if search_queries:
            needle = ' OR '.join(str(q) + '*' for q in search_queries)
            query = self.db_cursor.execute(
                "select docid "
                "from fts_flashcards "
                "where fts_flashcards match ?",
                (needle, )
            )
            flashcard_ids = tuple(row['docid'] for row in query)

            if flashcard_ids:
                if len(flashcard_ids) == 1:
                    flashcard_ids = f'({flashcard_ids[0]})'
                else:
                    flashcard_ids = str(flashcard_ids)

                flashcards = self._get_flashcards(
                    request=(
                        f'where id in {flashcard_ids} and '
                        f'user_id = {user_id}'
                    )
                )
                flashcard_container.extend(flashcards)

        return flashcard_container

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

    def get_source_tags(self, user_id):
        query = self.db_cursor.execute(
            'SELECT distinct(source) as tag '
            'FROM flashcards '
            'WHERE user_id = :user_id '
            'ORDER BY created desc;',
            {'user_id': user_id}
        )
        source_tags = []
        for row in query:
            tag = (row['tag'] or '').strip()
            if tag:
                tag = normalize_value(value=tag, remove_trailing='.')
                source_tags.append(tag.capitalize() + '.')

        return source_tags
