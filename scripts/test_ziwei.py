import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

from chart import chart, lunar_birth, lunar_at
from ziwei_bridge import compare, prepare_inputs, render_markdown, run_engine, ROOT

NODE = os.environ.get('BAZI_NODE') or shutil.which('node')


class AdapterTests(unittest.TestCase):
    def test_dst_and_offsets_are_the_same_instant(self):
        a = prepare_inputs(chart('1990-07-01T15:10:00+09:00'), 'female', 'next-day')
        b = prepare_inputs(chart('1990-07-01T14:10:00+08:00'), 'female', 'next-day')
        self.assertEqual(a[0]['birthInfo'], b[0]['birthInfo'])
        self.assertEqual(a[0]['birthInfo']['hour'], 7)

    def test_solar_correction_once_and_subminute_boundary(self):
        b = chart('2014-11-13T15:14:33.600000+08:00', longitude=116.36, clock='mean', uncertainty=1)
        inputs = prepare_inputs(b, 'female', 'next-day')
        self.assertEqual({c['birthInfo']['hour'] for c in inputs}, {7, 8})
        self.assertEqual(inputs[0]['example_selected_wall_clock'], b['central']['selected_wall_clock'])

    def test_distinct_ziwei_late_zi_rules(self):
        b = chart('2014-11-13T23:30:00+08:00')
        self.assertEqual(prepare_inputs(b, 'female', 'next-day')[0]['birthInfo']['day'], 14)
        self.assertEqual(prepare_inputs(b, 'female', 'current-day')[0]['birthInfo']['day'], 13)

    def test_midnight_and_23_boundaries(self):
        for time, rule, count in [('23:00', 'next-day', 2), ('00:00', 'next-day', 1),
                                   ('00:00', 'current-day', 2)]:
            b = chart('2014-11-13T'+time+':00+08:00', uncertainty=1)
            self.assertEqual(len(prepare_inputs(b, 'male', rule)), count, (time, rule))

    def test_missing_gender_and_policy_rejected(self):
        b = chart('2014-11-13T15:16:00+08:00')
        for gender, policy, day in [(None, 'all', 'next-day'), ('female', 'bad', 'next-day'),
                                    ('female', 'all', 'bad')]:
            with self.assertRaises(ValueError):
                compare(b, gender, policy, day)

    def test_missing_runtime_is_actionable(self):
        with patch.dict(os.environ, {'BAZI_NODE': ''}), patch('ziwei_bridge.shutil.which', return_value=None):
            with self.assertRaisesRegex(ValueError, 'Node.js'):
                run_engine([])

    def test_bundle_and_sources_match_manifest(self):
        m = json.loads((ROOT/'provenance.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256((ROOT/'engine.cjs').read_bytes()).hexdigest(), m['bundle_sha256'])
        for name, digest in m['local_sources_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), digest, name)
        self.assertEqual({p['name'] for p in m['runtime_packages']},
                         {'iztro', 'lunar-javascript', 'lunar-lite', 'dayjs', 'i18next', 'lunar-typescript'})
        notices = (ROOT/'THIRD_PARTY_NOTICES.txt').read_text(encoding='utf-8')
        for p in m['runtime_packages']:
            self.assertIn(p['name']+'@'+p['version'], notices)


@unittest.skipUnless(NODE, 'Ziwei integration requires Node.js 18+')
class EngineTests(unittest.TestCase):
    def test_child_leap_month_variants(self):
        b = chart('2014-11-13T15:16:00+08:00', 'female', 116.36, 'apparent')
        z = compare(b, 'female')
        self.assertEqual(b['central']['pillars'], ['甲午', '乙亥', '戊子', '庚申'])
        self.assertEqual([v['central']['chart']['mingGongBranch'] for v in z['variants']], [3, 2, 3, 2])
        self.assertEqual([v['central']['chart']['shenGongBranch'] for v in z['variants']], [7, 6, 7, 6])
        self.assertFalse(z['same_structure_across_selected_policies'])
        self.assertTrue(all(v['structure_stable_in_scanned_range'] for v in z['variants']))
        md = render_markdown({**b, 'ziwei': z})
        self.assertIn('太阴', md)
        self.assertIn('紫微', md)
        self.assertIn('不能强行合并', md)

    def test_nonleap_policies_agree(self):
        z = compare(chart('2014-11-30T15:16:00+08:00'), 'male')
        self.assertTrue(z['same_structure_across_selected_policies'])

    def test_uncertain_time_is_preserved_in_each_policy(self):
        z = compare(chart('2014-11-13T15:00:00+08:00', uncertainty=1), 'female')
        self.assertTrue(all(len(v['candidates']) == 2 for v in z['variants']))
        self.assertTrue(all(not v['structure_stable_in_scanned_range'] for v in z['variants']))

    def test_deterministic_natal_output_has_no_midpoint_bazi_or_runtime_age(self):
        requests = [{'birthInfo': {'year': 2014, 'month': 11, 'day': 13, 'hour': 8, 'gender': 'female'},
                     'leapMonth': 'split'}] * 2
        a, b = run_engine(requests)
        self.assertEqual(a, b)
        self.assertNotIn('fourPillars', a['lunarInfo'])
        self.assertNotIn('fourPillarsLunar', a['lunarInfo'])
        self.assertNotIn('currentAge', a)
        self.assertNotIn('currentDaXianIndex', a)
        self.assertTrue(all('isCurrentDaXian' not in p for p in a['palaces']))

    def test_invalid_engine_inputs_fail(self):
        for update in [{'day': 30, 'month': 2}, {'hour': 12}, {'hour': -1},
                       {'gender': 'other'}, {'year': 1949}, {'hour': 1.5}]:
            b = {'year': 2014, 'month': 11, 'day': 13, 'hour': 8, 'gender': 'female', **update}
            with self.assertRaises(ValueError):
                run_engine([{'birthInfo': b, 'leapMonth': 'split'}])

    def test_lunar_input_matches_gregorian(self):
        converted = lunar_birth('2014-09-21', '15:16', '+08:00', True)
        self.assertEqual(compare(chart(converted), 'female'),
                         compare(chart('2014-11-13T15:16:00+08:00'), 'female'))

    def test_structure_across_96_charts_and_independent_palace_formula(self):
        from datetime import datetime
        for year in (1950, 1988, 2014, 2050):
            requests = [{'birthInfo': {'year': year, 'month': m, 'day': 10, 'hour': h,
                                      'gender': 'female' if h == 8 else 'male'}, 'leapMonth': 'prev-month'}
                        for m in range(1, 13) for h in (0, 8)]
            for request, c in zip(requests, run_engine(requests)):
                b = request['birthInfo']
                self.assertEqual(sorted(p['branch'] for p in c['palaces']), list(range(12)))
                self.assertEqual(len({p['name'] for p in c['palaces']}), 12)
                stars = [s['name'] for p in c['palaces'] for s in p['stars'] if s['type'] == 'major']
                self.assertEqual(len(stars), 14)
                self.assertEqual(len(set(stars)), 14)
                self.assertEqual(sum(bool(s.get('siHua')) for p in c['palaces'] for s in p['stars']), 4)
                lunar = lunar_at(datetime(b['year'], b['month'], b['day']))
                # 寅起正月，逆数生时安命、顺数生时安身；prev-month preserves the month number.
                month = abs(lunar.getMonth())
                self.assertEqual(c['mingGongBranch'], (month + 1 - b['hour']) % 12)
                self.assertEqual(c['shenGongBranch'], (month + 1 + b['hour']) % 12)
                for palace in c['palaces']:
                    self.assertEqual(palace['oppositeBranch'], (palace['branch'] + 6) % 12)

    def test_cli_markdown_and_option_validation(self):
        script = str(Path(__file__).parent/'chart.py')
        args = [sys.executable, '-X', 'utf8', script, '--birth', '2014-11-13T15:16:00+08:00']
        result = subprocess.run(args + ['--ziwei', '--gender', 'female', '--format', 'markdown'],
                                capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('闰月分半', result.stdout)
        bad = subprocess.run(args + ['--ziwei-leap', 'split'], capture_output=True, text=True, encoding='utf-8')
        self.assertNotEqual(bad.returncode, 0)


if __name__ == '__main__':
    unittest.main()
