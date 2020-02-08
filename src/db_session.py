import bisect
import random
import sqlite3
import logging

from datetime import datetime
from itertools import groupby
from typing import List
from itertools import zip_longest

from src.flashcard import Flashcard, FlashcardContainer
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

    def __init__(self, database, *, flashcard_type, setup_db=False):
        self.flashcard_type = normalize_value(flashcard_type, to_lower=True)
        self.db_conn = sqlite3.connect(
            database, detect_types=sqlite3.PARSE_DECLTYPES
        )
        self.db_conn.row_factory = sqlite3.Row
        self.db_cursor = self.db_conn.cursor()
        if setup_db:
            self.setup_users_table()
            self.setup_flashcards_table()
            self.setup_flashcard_example_table()
            self.setup_flashcard_review_history_table()
            self.setup_full_text_search()

        #self.db_conn.set_trace_callback(self.trace_callback)

    def __str__(self):
        return '<{0}[conn:{1}]>'.format(
            self.__class__.__name__,
            self.db_conn
        )

    def close(self):
        self.db_cursor.close()
        self.db_conn.close()
        
    def trace_callback(self, statement):
        logger.info(f'SQL: {statement}')

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

    def setup_flashcard_review_history_table(self):
        self.db_cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='flashcard_review_history';
        """)
        flashcard_review_history_table = self.db_cursor.fetchone()
        if flashcard_review_history_table is None:
            with open('sql/flashcard_review_history.sql') as fh:
                flashcard_review_history_table = fh.read()
            self.db_cursor.execute(flashcard_review_history_table)
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
                'WHERE user_id = :user_id AND '
                '      flashcard_type = :flashcard_type; ',
                {
                    'user_id': user_id,
                    'flashcard_type': self.flashcard_type
                }
            )
        else:
            query = self.db_cursor.execute(
                'SELECT count(*) '
                'FROM flashcards '
                'WHERE user_id = :user_id AND '
                '      flashcard_type = :flashcard_type AND '
                '      datetime(review_timestamp, "localtime") <= :review',
                {
                    'user_id': user_id,
                    'flashcard_type': self.flashcard_type,
                    'review': review_timestamp
                }
            )
        return query.fetchone()['count(*)']

    def _get_flashcards(
            self, request: str, request_params: dict=None
    ) -> List[Flashcard]:

        request_params = request_params or {}
        query = self.db_cursor.execute(
            f'SELECT '
            f'    id as flashcard_id, '
            f'    flashcard_type, '
            f'    user_id, '
            f'    question, '
            f'    answer, '
            f'    review_timestamp, '
            f'    review_version, '
            f'    source, '
            f'    explanation, '
            f'    phonetic_transcription, '
            f'    created '
            f'FROM flashcards '
            f'{request}',
            request_params
        )
        flashcards = []
        for row in query.fetchall():
            data = dict(row)
            examples = self.db_cursor.execute(
                'SELECT example '
                'FROM flashcard_example '
                'WHERE flashcard_id = :flashcard_id',
                {'flashcard_id': data['flashcard_id']}
            )
            data['examples'] = [r['example'] for r in examples]

            flashcard = Flashcard(
                user_id=data['user_id'],
                flashcard_type=data['flashcard_type'],
                question=data['question'],
                answer=data['answer'],
                created=convert_datetime_to_local(data['created']),
                review_timestamp=convert_datetime_to_local(
                    data['review_timestamp']
                ),
                review_version=data['review_version'],
                flashcard_id=data['flashcard_id'],
                phonetic_transcription=data['phonetic_transcription'],
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
                f'      flashcard_type = :flashcard_type AND '
                f'      datetime(review_timestamp, "localtime") <= :now '
                f'ORDER BY '
                f'      review_version DESC, '
                f'      datetime(review_timestamp, "localtime")'
            ),
            request_params={
                'flashcard_type': self.flashcard_type,
                'user_id': user_id,
                'now': datetime_now()
            }
        )

        text_flashcards = []
        audio_flashcards = []
        for _flashcard in flashcards:
            if _flashcard.is_audio_type():
                audio_flashcards.append(_flashcard)
            else:
                text_flashcards.append(_flashcard)

        def _shuffle(flashcards):
            group_by_date = groupby(
                flashcards,
                key=lambda f: (f['review_version'], f['review_timestamp'].date())
            )
            shuffled_flashcards = []
            for key, data in group_by_date:
                flashcards_by_date = list(data)
                random.shuffle(flashcards_by_date)
                shuffled_flashcards.extend(flashcards_by_date)
            return shuffled_flashcards

        shuffled_audio_flashcards = _shuffle(audio_flashcards)
        shuffled_text_flashcards = _shuffle(text_flashcards)

        flashcard_container = FlashcardContainer()
        _zip_audio_text = zip_longest(
            shuffled_audio_flashcards, shuffled_text_flashcards
        )
        for audio_f, text_f in _zip_audio_text:
            if text_f:
                flashcard_container.add(text_f)
            if audio_f:
                flashcard_container.add(audio_f)

        return flashcard_container

    def add_flashcard(self, flashcard: Flashcard) -> None:
        with self.db_conn:
            self.db_cursor.execute(
                'INSERT INTO flashcards('
                '    flashcard_type, '
                '    user_id, '
                '    question, '
                '    answer, '
                '    review_timestamp, '
                '    review_version, '
                '    source, '
                '    explanation, '
                '    phonetic_transcription, '
                '    created '
                ') '
                'VALUES ('
                '    :flashcard_type, '
                '    :user_id, '
                '    :question, '
                '    :answer, '
                '    :review_timestamp, '
                '    :review_version, '
                '    :source, '
                '    :explanation, '
                '    :phonetic_transcription, '
                '    :created '
                ') ',
                {
                    'flashcard_type': flashcard.flashcard_type,
                    'user_id': flashcard.user_id,
                    'question': flashcard.question,
                    'answer': flashcard.answer,
                    'review_timestamp': datetime_change_timezone(
                        flashcard.review_timestamp, offset=0
                    ),
                    'review_version': flashcard.review_version,
                    'source': flashcard.source,
                    'explanation': flashcard.explanation,
                    'phonetic_transcription': flashcard.phonetic_transcription,
                    'created': datetime_change_timezone(
                        flashcard.created, offset=0
                    )
                }
            )
            flashcard.flashcard_id = self.db_cursor.lastrowid

            for example in flashcard.examples or []:
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
                '   question=:question, '
                '   answer=:answer, '
                '   source=:source, '
                '   explanation=:explanation, '
                '   phonetic_transcription=:phonetic_transcription '
                'WHERE id=:flashcard_id',
                {
                    'flashcard_id': flashcard.flashcard_id,
                    'question': flashcard.question,
                    'answer': flashcard.answer,
                    'source': flashcard.source,
                    'explanation': flashcard.explanation,
                    'phonetic_transcription': flashcard.phonetic_transcription
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
                DELETE FROM flashcard_review_history 
                WHERE flashcard_id={flashcard.flashcard_id};
                DELETE FROM flashcard_example
                WHERE flashcard_id={flashcard.flashcard_id};
                DELETE FROM flashcards
                WHERE id={flashcard.flashcard_id};
            """)

    def update_flashcard_review_state(
            self,
            flashcard_id: int,
            current_review_timestamp: datetime,
            current_result: str,
            next_review_timestamp: datetime,
            next_review_version: int,
    ) -> None:
        with self.db_conn:
            self.db_cursor.execute(
                'UPDATE flashcards SET '
                '   review_timestamp=:review_timestamp, '
                '   review_version=:review_version '
                'WHERE id=:flashcard_id',
                {
                    'flashcard_id': flashcard_id,
                    'review_timestamp': datetime_change_timezone(
                        next_review_timestamp, offset=0
                    ),
                    'review_version': next_review_version
                }
            )
            self.db_cursor.execute(
                'INSERT INTO flashcard_review_history('
                '   flashcard_id,'
                '   review_timestamp, '
                '   result'
                ') '
                'VALUES (:flashcard_id, :review_timestamp, :result)',
                {
                    'flashcard_id': flashcard_id,
                    'review_timestamp': datetime_change_timezone(
                        current_review_timestamp, offset=0
                    ),
                    'result': current_result
                }
            )

    def search(self, *search_queries, user_id) -> FlashcardContainer:
        flashcard_container = FlashcardContainer()

        search_queries = [
            s.strip() for s in search_queries if s.strip()
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
                        f'where id in {flashcard_ids} AND '
                        f'      user_id = :user_id AND '
                        f'      flashcard_type = :flashcard_type '
                    ),
                    request_params={
                        'user_id': user_id,
                        'flashcard_type': self.flashcard_type
                    }
                )
                flashcard_container.extend(flashcards)

        return flashcard_container

    def get_flashcards(self, user_id) -> FlashcardContainer:
        flashcards = self._get_flashcards(
            request=(
                f'where user_id = :user_id AND '
                f'      flashcard_type = :flashcard_type '
            ),
            request_params={
                'user_id': user_id,
                'flashcard_type': self.flashcard_type
            }
        )

        flashcard_container = FlashcardContainer()
        flashcard_container.extend(flashcards)
        return flashcard_container

    def get_vis_by_date(self, user_id):
        query = self.db_cursor.execute(
            'SELECT '
            '   strftime("%Y-%m-%d", review_timestamp, "localtime") as key, '
            '   count(*) as value '
            'FROM flashcards '
            'WHERE user_id = :user_id and flashcard_type = :flashcard_type '
            'GROUP BY strftime("%Y-%m-%d", review_timestamp, "localtime") '
            'ORDER BY strftime("%Y-%m-%d", review_timestamp, "localtime");',
            {
                'user_id': user_id,
                'flashcard_type': self.flashcard_type
            }
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

    def get_recent_explanations(self, user_id, limit=1):
        query = self.db_cursor.execute(
            "SELECT explanation "
            "FROM flashcards "
            "WHERE user_id = :user_id and flashcard_type = :flashcard_type "
            "      and explanation is not null "
            "      and explanation != '' "
            "ORDER BY created desc "
            "LIMIT :limit;",
            {
                'user_id': user_id,
                'flashcard_type': self.flashcard_type,
                'limit': limit
            }
        )
        recent_explanations = [row['explanation'] for row in query]
        return recent_explanations

    def get_source_tags(self, user_id):
        query = self.db_cursor.execute(
            'SELECT distinct(source) as tag '
            'FROM flashcards '
            'WHERE user_id = :user_id and flashcard_type = :flashcard_type '
            'ORDER BY created desc;',
            {
                'user_id': user_id,
                'flashcard_type': self.flashcard_type
            }
        )
        source_tags = []
        for row in query:
            tag = (row['tag'] or '').strip()
            if tag:
                tag = normalize_value(value=tag, remove_trailing='.')
                source_tags.append(tag.capitalize() + '.')
        source_tags.sort(reverse=True)
        return source_tags

    def get_prev_review_timestamp(self, flashcard):
        query = self.db_cursor.execute(
            'SELECT * '
            'FROM flashcard_review_history '
            'WHERE flashcard_id = :flashcard_id '
            'ORDER BY review_timestamp desc',
            {
                'flashcard_id': flashcard.flashcard_id,
            }
        )
        row = query.fetchone()
        if row:
            previous_review_timestamp = convert_datetime_to_local(
                row['review_timestamp']
            )
        else:
            previous_review_timestamp = flashcard.created
        return previous_review_timestamp
