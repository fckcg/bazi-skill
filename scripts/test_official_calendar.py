"""Offline comparison against separately retrieved official calendar fixtures."""
from datetime import datetime
import json
from pathlib import Path
import unittest
from chart import lunar_at, solar_datetime

FIXTURE = Path(__file__).resolve().parent.parent/'references/calendar-fixtures.json'


def engine_table(year):
    out = {}
    for name, solar in lunar_at(datetime(year,6,15,12)).getJieQiTable().items():
        value = solar_datetime(solar)
        if value.year == year:
            out['冬至' if name == 'DONG_ZHI' else name] = value
    return out


class OfficialCalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(FIXTURE.read_text(encoding='utf-8'))
        cls.tables = {y:engine_table(y) for y in range(1950,2051)}

    def test_hko_1950_2050_dates_with_documented_midnight_difference(self):
        rows = self.data['hko_dates']
        self.assertEqual(len(rows),2424)
        self.assertEqual({r['year'] for r in rows},set(range(1950,2051)))
        self.assertEqual(len({(r['year'],r['term']) for r in rows}),2424)
        differences = {}
        for r in rows:
            actual = self.tables[r['year']][r['term']]
            if actual.date().isoformat() != r['date']:
                differences[(r['year'],r['term'])] = (r['date'],actual.isoformat())
        # This is an explicit regression exception, NOT a statement that
        # the differing engine date has been validated against HKO.
        self.assertEqual(differences,{(1979,'大寒'):('1979-01-21','1979-01-20T23:59:56+08:00')})

    def test_naoj_2010_2027_times(self):
        rows = self.data['naoj_times']
        self.assertEqual(len(rows),432)
        self.assertEqual({r['year'] for r in rows},set(range(2010,2028)))
        self.assertEqual(len({(r['year'],r['term']) for r in rows}),432)
        for r in rows:
            with self.subTest(year=r['year'],term=r['term']):
                delta = abs((self.tables[r['year']][r['term']]-datetime.fromisoformat(r['beijing_time'])).total_seconds())
                self.assertLessEqual(delta,90)


if __name__ == '__main__':
    unittest.main()
