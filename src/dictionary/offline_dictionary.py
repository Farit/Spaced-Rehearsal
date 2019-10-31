import logging
import json
import sqlite3
import enum

logger = logging.getLogger(__name__)


class OfflineDict:

    def __init__(self, lang, dictionary_db_path):
        self.hits = 0
        self.missing_value_sentinel = object()
        self.db_conn = sqlite3.connect(
            dictionary_db_path,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        self.db_conn.row_factory = sqlite3.Row
        self.db_cursor = self.db_conn.cursor()
        self.lang = lang
        self.db_name = 'offline_dictionary'
        self.setup_table()

    def setup_table(self):
        self.db_cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='{db_name}';
        """.format(db_name=self.db_name))
        table = self.db_cursor.fetchone()
        if table is None:
            with open('sql/offline_dictionary.sql') as fh:
                table = fh.read()
            self.db_cursor.execute(table)
            self.db_conn.commit()

    async def close(self):
        self.db_cursor.close()
        self.db_conn.close()

    def get(self, key, field=None, grammatical_feature=None):
        field = (
            OfflineDictFields(field).value
            if field is not None else None
        )
        grammatical_feature = (
            OfflineDictGrammaticalFeatures(grammatical_feature).value
            if grammatical_feature is not None else None
        )

        if field is None and grammatical_feature is None:
            self.db_cursor.execute(
                f'SELECT * '
                f'FROM {self.db_name} '
                f'WHERE lang=? and key=?',
                (self.lang, key)
            )
        elif field is not None and grammatical_feature is None:
            self.db_cursor.execute(
                f'SELECT * '
                f'FROM {self.db_name} '
                f'WHERE lang=? and key=? and field=?',
                (self.lang, key, field)
            )
        elif field is None and grammatical_feature is not None:
            self.db_cursor.execute(
                f'SELECT * '
                f'FROM {self.db_name} '
                f'WHERE lang=? and key=? and grammatical_feature=?',
                (self.lang, key, grammatical_feature)
            )
        else:
            self.db_cursor.execute(
                f'SELECT * '
                f'FROM {self.db_name} '
                f'WHERE lang=? and key=? and field=? and '
                f'grammatical_feature=?',
                (self.lang, key, field, grammatical_feature)
            )

        res = self.db_cursor.fetchone()
        if not res:
            return self.missing_value_sentinel

        self.hits += 1
        return json.loads(res['value'])['value']

    def set(self, key, value, field=None, grammatical_feature=None):
        field = (
            OfflineDictFields(field).value
            if field is not None else None
        )
        grammatical_feature = (
            OfflineDictGrammaticalFeatures(grammatical_feature).value
            if grammatical_feature is not None else None
        )
        current_value = self.get(
            key=key, field=field, grammatical_feature=grammatical_feature
        )
        if current_value is self.missing_value_sentinel:
            with self.db_conn:
                if field is None and grammatical_feature is None:
                    self.db_cursor.execute(
                        f'INSERT INTO {self.db_name}'
                        f'(lang, key, value) '
                        f'VALUES '
                        f'(:lang, :key, :value)',
                        {
                            'lang': self.lang,
                            'key': key,
                            'value': json.dumps({'value': value})
                        }
                    )
                elif field is not None and grammatical_feature is None:
                    self.db_cursor.execute(
                        f'INSERT INTO {self.db_name}'
                        f'(lang, key, value, field) '
                        f'VALUES '
                        f'(:lang, :key, :value, :field)',
                        {
                            'lang': self.lang,
                            'key': key,
                            'value': json.dumps({'value': value}),
                            'field': field
                        }
                    )
                elif field is None and grammatical_feature is not None:
                    self.db_cursor.execute(
                        f'INSERT INTO {self.db_name}'
                        f'(lang, key, value, grammatical_feature) '
                        f'VALUES '
                        f'(:lang, :key, :value, :grammatical_feature)',
                        {
                            'lang': self.lang,
                            'key': key,
                            'value': json.dumps({'value': value}),
                            'grammatical_feature': grammatical_feature
                        }
                    )
                else:
                    self.db_cursor.execute(
                        f'INSERT INTO {self.db_name}'
                        f'(lang, key, value, field, grammatical_feature) '
                        f'VALUES '
                        f'(:lang, :key, :value, :field, :grammatical_feature)',
                        {
                            'lang': self.lang,
                            'key': key,
                            'value': json.dumps({'value': value}),
                            'field': field,
                            'grammatical_feature': grammatical_feature
                        }
                    )
        else:
            with self.db_conn:
                if field is None and grammatical_feature is None:
                    self.db_cursor.execute(
                        f'UPDATE {self.db_name} '
                        f'set value=:value '
                        f'where key=:key and lang=:lang',
                        {
                            'lang': self.lang,
                            'key': key,
                            'value': json.dumps({'value': value})
                        }
                    )
                elif field is not None and grammatical_feature is None:
                    self.db_cursor.execute(
                        f'UPDATE {self.db_name} '
                        f'set value=:value '
                        f'where key=:key and field=:field and lang=:lang',
                        {
                            'lang': self.lang,
                            'key': key,
                            'value': json.dumps({'value': value}),
                            'field': field
                        }
                    )
                elif field is None and grammatical_feature is not None:
                    self.db_cursor.execute(
                        f'UPDATE {self.db_name} '
                        f'set value=:value '
                        f'where key=:key and lang=:lang and '
                        f'grammatical_feature=:grammatical_feature',
                        {
                            'lang': self.lang,
                            'key': key,
                            'value': json.dumps({'value': value}),
                            'grammatical_feature': grammatical_feature
                        }
                    )
                else:
                    self.db_cursor.execute(
                        f'UPDATE {self.db_name} '
                        f'set value=:value '
                        f'where key=:key and field=:field and lang=:lang and '
                        f'grammatical_feature=:grammatical_feature',
                        {
                            'lang': self.lang,
                            'key': key,
                            'value': json.dumps({'value': value}),
                            'field': field,
                            'grammatical_feature': grammatical_feature
                        }
                    )


class OfflineDictFields(enum.Enum):
    PRONUNCIATION = 'pronunciation'
    LEMMAS = 'lemmas'


class OfflineDictGrammaticalFeatures(enum.Enum):
    CONJUNCTION = "conjunction"
    DETERMINER = "determiner"
    ADJECTIVE = "adjective"
    PREPOSITION = "preposition"
    NOUN = "noun"
    VERB = 'verb'
    ADVERB = 'adverb'
    PRONOUN = 'pronoun'
