import json
from pathlib import Path
import subprocess
import sys
import unittest
from chart import chart, lunar_birth

SCRIPT = Path(__file__).with_name('chart.py')


def cli(*args):
    return subprocess.run([sys.executable, '-B', '-X', 'utf8', str(SCRIPT), *args],
                          capture_output=True, encoding='utf-8')


class LunarInputTests(unittest.TestCase):
    def test_leap_month_known_date(self):
        converted = lunar_birth('2014-09-21', '15:16', '+08:00', True)
        self.assertEqual(converted, '2014-11-13T15:16:00+08:00')
        self.assertEqual(chart(converted)['central']['pillars'], ['甲午', '乙亥', '戊子', '庚申'])

    def test_regular_and_leap_month_differ(self):
        self.assertEqual(lunar_birth('2014-09-21', '15:16', '+08:00', False), '2014-10-14T15:16:00+08:00')
        self.assertNotEqual(lunar_birth('2014-09-21', '15:16', '+08:00'), lunar_birth('2014-09-21', '15:16', '+08:00', True))

    def test_another_leap_month(self):
        self.assertEqual(lunar_birth('2023-02-01', '00:00', '+08:00', True), '2023-03-22T00:00:00+08:00')

    def test_explicit_dst_preserved(self):
        converted = lunar_birth('1990-04-21', '10:30:45', '+09:00')
        self.assertTrue(converted.endswith('T10:30:45+09:00'))
        self.assertEqual(chart(converted)['central']['beijing_time'][-14:], '09:30:45+08:00')

    def test_reject_invalid_lunar_inputs(self):
        cases = [('2014-09-30','15:16','+08:00',True),
                 ('2015-09-21','15:16','+08:00',True),
                 ('2014-13-01','15:16','+08:00',False),
                 ('2014-09-00','15:16','+08:00',False),
                 ('2014-9-21','15:16','+08:00',True),
                 ('2014-09-21','25:00','+08:00',True),
                 ('2014-09-21','15:16','UTC+8',True),
                 ('2014-09-21','15:16','+07:60',True),
                 ('2014-09-21','15:16','-05:00',True),
                 ('2050-12-30','15:16','+08:00',False)]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                lunar_birth(*case)

    def test_cli_lunar_metadata_and_equivalence(self):
        result = cli('--lunar-date','2014-09-21','--lunar-leap','--time','15:16','--utc-offset=+08:00','--gender','female')
        self.assertEqual(result.returncode,0,result.stderr)
        data = json.loads(result.stdout)
        solar = json.loads(cli('--birth','2014-11-13T15:16:00+08:00','--gender','female').stdout)
        self.assertEqual(data['central'],solar['central'])
        self.assertEqual(data['input']['calendar'],'lunar')
        self.assertTrue(data['input']['leap_month'])
        self.assertEqual(data['input']['converted_gregorian_birth'],'2014-11-13T15:16:00+08:00')

    def test_cli_missing_or_conflicting_arguments(self):
        for args in [('--lunar-date','2014-09-21'),
                     ('--birth','2014-11-13T15:16:00+08:00','--lunar-leap'),
                     ('--birth','2014-11-13T15:16:00+08:00','--lunar-date','2014-09-21'),
                     ('--lunar-date','2015-09-21','--lunar-leap','--time','15:16','--utc-offset=+08:00')]:
            with self.subTest(args=args):
                result=cli(*args)
                self.assertEqual(result.returncode,2)
                self.assertNotIn('Traceback',result.stderr)


if __name__ == '__main__':
    unittest.main()
