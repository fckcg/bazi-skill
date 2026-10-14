import unittest
from datetime import datetime, timedelta
from chart import chart, lunar_at, solar_datetime


class ChartTests(unittest.TestCase):
    def test_known_chart(self):
        r = chart('2014-11-13T15:16:00+08:00', 'female', 117.03, 'apparent', uncertainty=5)
        self.assertEqual(r['central']['pillars'], ['甲午', '乙亥', '戊子', '庚申'])
        self.assertTrue(r['pillars_stable_in_scanned_range'])
        self.assertEqual(r['central']['yun']['sequence'][0]['ganzhi'], '甲戌')
        self.assertEqual(r['central']['yun']['direction'], 'reverse')
        self.assertEqual(r['central']['yun']['start_civil_time'], '2016-10-19T11:16:00+08:00')

    def test_independent_official_terms(self):
        # HKO 2014cal11.pdf / 2014cal12.pdf and NAOJ 2014 calendar,
        # rounded to minutes; compare within 60 seconds, not exact seconds.
        table = lunar_at(datetime(2014, 11, 13)).getJieQiTable()
        for name, stamp in [('立冬', '2014-11-07T20:07:00+08:00'),
                            ('大雪', '2014-12-07T13:04:00+08:00')]:
            self.assertLess(abs((solar_datetime(table[name])-datetime.fromisoformat(stamp)).total_seconds()), 60)

    def test_lichun_changes_year_and_month(self):
        term = solar_datetime(lunar_at(datetime(2024, 2, 5)).getJieQiTable()['立春'])
        before = chart((term-timedelta(seconds=1)).isoformat())['central']['pillars']
        after = chart(term.isoformat())['central']['pillars']
        self.assertEqual(before[:2], ['癸卯', '乙丑'])
        self.assertEqual(after[:2], ['甲辰', '丙寅'])

    def test_lidong_interval(self):
        r = chart('2014-11-07T20:06:40+08:00', uncertainty=1)
        self.assertFalse(r['pillars_stable_in_scanned_range'])
        self.assertEqual({c['pillars'][1] for c in r['candidates']}, {'甲戌', '乙亥'})

    def test_hour_boundary(self):
        r = chart('2014-11-13T15:00:00+08:00', uncertainty=1)
        self.assertEqual({c['pillars'][3] for c in r['candidates']}, {'己未', '庚申'})

    def test_day_rules(self):
        a = chart('2014-11-13T23:30:00+08:00', day_rule='midnight')['central']['pillars']
        b = chart('2014-11-13T23:30:00+08:00', day_rule='23')['central']['pillars']
        c = chart('2014-11-13T23:30:00+08:00', day_rule='early-late')['central']['pillars']
        self.assertEqual(a[2:], ['戊子', '壬子'])
        self.assertEqual(b[2:], ['己丑', '甲子'])
        self.assertEqual(c[2:], ['戊子', '甲子'])

    def test_same_instant_offsets(self):
        a = chart('2014-11-13T15:16:00+08:00')['central']['pillars']
        b = chart('2014-11-13T07:16:00+00:00')['central']['pillars']
        self.assertEqual(a, b)

    def test_dst_explicit_offset(self):
        a = chart('1990-05-15T10:30:00+09:00')['central']['pillars']
        b = chart('1990-05-15T09:30:00+08:00')['central']['pillars']
        self.assertEqual(a, b)

    def test_solar_clock_does_not_move_term_instant(self):
        r = chart('2014-11-07T20:10:00+08:00', longitude=100, clock='mean')
        self.assertEqual(r['central']['pillars'][1], '乙亥')

    def test_mean_and_apparent_are_distinct(self):
        a = chart('2014-11-13T15:00:00+08:00', longitude=117.03, clock='mean')
        b = chart('2014-11-13T15:00:00+08:00', longitude=117.03, clock='apparent')
        self.assertEqual(a['central']['pillars'][3], '己未')
        self.assertEqual(b['central']['pillars'][3], '庚申')

    def test_leap_day(self):
        a = chart('2000-02-28T12:00:00+08:00')['central']['pillars'][2]
        b = chart('2000-02-29T12:00:00+08:00')['central']['pillars'][2]
        c = chart('2000-03-01T12:00:00+08:00')['central']['pillars'][2]
        self.assertEqual([a, b, c], ['丙辰', '丁巳', '戊午'])

    def test_gender_direction(self):
        self.assertEqual(chart('2014-11-13T15:16:00+08:00', 'male')['central']['yun']['direction'], 'forward')
        self.assertEqual(chart('2015-11-13T15:16:00+08:00', 'female')['central']['yun']['direction'], 'forward')

    def test_reject_invalid(self):
        for kwargs in [{'birth': '2014-11-13T15:16:00'},
                       {'birth': '2014-11-13T15:16:00+08:00', 'uncertainty': -1},
                       {'birth': '2014-11-13T15:16:00+08:00', 'longitude': float('nan')},
                       {'birth': '2014-11-13T15:16:00+08:00', 'clock': 'apparent'},
                       {'birth': '1900-01-01T12:00:00+08:00'},
                       {'birth': '2014-11-13T15:16:00+08:00', 'day_rule': 'unknown'}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                chart(**kwargs)

    def test_term_review_threshold(self):
        r = chart('2014-11-07T20:07:00+08:00')
        self.assertEqual(r['near_solar_terms_requiring_review'][0]['term'], '立冬')
        self.assertTrue(r['pillars_stable_in_scanned_range'])
        self.assertEqual(chart('2014-11-13T15:16:00+08:00')['near_solar_terms_requiring_review'], [])

    def test_lunar_date_keeps_astronomical_clock(self):
        r = chart('2014-11-13T00:10:00+08:00', longitude=100, clock='mean')
        self.assertIn('廿一', r['central']['lunar_date'])
        self.assertIn('二十', r['central']['selected_wall_clock_lunar_date'])

    def test_interval_includes_midnight(self):
        r = chart('2014-11-14T00:00:00+08:00', uncertainty=1)
        self.assertEqual({c['pillars'][2] for c in r['candidates']}, {'戊子', '己丑'})


if __name__ == '__main__':
    unittest.main()
