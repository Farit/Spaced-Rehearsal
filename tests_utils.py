import unittest

from datetime import datetime, timezone, timedelta

from utils import normalize_value, datetime_change_timezone


class TestCaseFlashcard(unittest.TestCase):

    def test_datetime_change_timezone_with_naive_timezone(self):
        naive_datetime = datetime(2017, 12, 1, 11, 16, 6, 912571)
        test_offests = [
            # a half an hour
            0.5 * 60 * 60,
            # 1 hour
            1 * 60 * 60,
            # 2 hour
            -(1 * 60 * 60),
            # 3 hour
            1 * 60 * 60,
            # 3.5 hour
            -(1.5 * 60 * 60),
        ]
        for test_offest in test_offests:
            send_datetime = naive_datetime
            send_datetime = send_datetime.replace(tzinfo=timezone.utc)

            test_offest = test_offest if test_offest >= 0  else -test_offest
            expected = naive_datetime + timedelta(seconds=test_offest)
            expected = expected.replace(
                tzinfo=timezone(timedelta(seconds=test_offest))
            )

            msg = f'send: {send_datetime}, offset: {timedelta(seconds=test_offest)}'
            with self.subTest(msg):
                returned = datetime_change_timezone(
                    send_datetime, offset=test_offest
                )

                self.assertEqual(
                    returned, expected,
                    f'returned: {returned},  '
                    f'expected: {expected}'
                )

    def test_datetime_change_timezone_with_aware_timezone(self):
        naive_datetime = datetime(2017, 12, 1, 11, 16, 6, 912571)
        test_offests = [
            # a half an hour
            0.5 * 60 * 60,
            # 1 hour
            1 * 60 * 60,
            # 2 hour
            -(1 * 60 * 60),
            # 3 hour
            1 * 60 * 60,
            # 3.5 hour
            -(1.5 * 60 * 60),
        ]
        for test_offest in test_offests:
            send_datetime = naive_datetime + timedelta(seconds=3 * 60 * 60)
            send_datetime = send_datetime.replace(
                tzinfo=timezone(timedelta(seconds=3 * 60 * 60))
            )

            test_offest = test_offest if test_offest >= 0  else -test_offest
            expected = naive_datetime + timedelta(seconds=test_offest)
            expected = expected.replace(
                tzinfo=timezone(timedelta(seconds=test_offest))
            )

            msg = f'send: {send_datetime}, offset: {timedelta(seconds=test_offest)}'
            with self.subTest(msg):
                returned = datetime_change_timezone(
                    send_datetime, offset=test_offest
                )

                self.assertEqual(
                    returned, expected,
                    f'returned: {returned},  '
                    f'expected: {expected}'
                )

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