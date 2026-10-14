import json
from pathlib import Path
import subprocess
import sys
import unittest
from chart import chart
from methods import facts, inspect_rule, load_registry, review_chart, select_profiles, ten_god

ROOT=Path(__file__).resolve().parent.parent
EXPECTED={'shen-xiaozhan','ren-tieqiao','xu-lewu','yu-chuntai','wan-minying','zhang-nan',
          'wei-qianli','liang-xiangrun','chen-suan','yuan-shushan','zou-wenyao','duan-jianye',
          'wu-junmin','he-jianzhong','zhong-yiming'}


def cli(*args):
    return subprocess.run([sys.executable,'-B','-X','utf8',str(ROOT/'scripts/chart.py'),*args],
                          capture_output=True,encoding='utf-8')


class MethodTests(unittest.TestCase):
    def setUp(self):
        self.c=chart('2014-11-13T15:16:00+08:00','female')

    def test_all_suggested_authors_have_independent_profiles(self):
        r=load_registry()
        self.assertEqual({p['id'] for p in r['profiles']},EXPECTED)
        self.assertEqual(len(r['profiles']),15)
        for p in r['profiles']:
            self.assertTrue((ROOT/'references'/p['reference_file']).is_file())
            self.assertTrue(p['project_checklist'])
            self.assertTrue(p['works'])
            self.assertTrue(all(s['url'].startswith('https://') and s['locator'] for s in p['sources']))

    def test_every_active_rule_has_checked_text_and_locator(self):
        r=load_registry();lookup={p['id']:p for p in r['profiles']}
        self.assertEqual(len({x['id'] for x in r['rules']}),len(r['rules']))
        for rule in r['rules']:
            self.assertEqual(lookup[rule['profile']]['source_status'],'text_excerpt_checked')
            self.assertIn(rule['id'],lookup[rule['profile']]['verified_rule_ids'])
            self.assertTrue(rule['locator'])
            self.assertTrue(rule['scope'])

    def test_unchecked_author_attribution_is_withheld(self):
        r=review_chart(self.c,'duan-jianye,liang-xiangrun,he-jianzhong')
        for p in r['method_results']:
            self.assertTrue(p['unverified_attribution_withheld'])
            self.assertEqual(p['rules'],[])
            self.assertEqual(p['project_evidence']['origin'],'project_shared_facts_not_author_rule')

    def test_ten_gods_all_relations_for_wu(self):
        expected={'甲':'七杀','乙':'正官','丙':'偏印','丁':'正印','戊':'比肩',
                  '己':'劫财','庚':'食神','辛':'伤官','壬':'偏财','癸':'正财'}
        self.assertEqual({g:ten_god('戊',g) for g in expected},expected)

    def test_real_chart_structural_evidence(self):
        f=facts(self.c['central']['pillars'])
        self.assertEqual(f['month_hidden_gods'],[{'stem':'壬','god':'偏财'},{'stem':'甲','god':'七杀'}])
        self.assertEqual({r['branch'] for r in f['same_element_roots']},{'午','申'})
        self.assertTrue(any(r['type']=='冲' and r['branches']==['午','子'] for r in f['branch_relations']))
        self.assertTrue(all(r['event_meaning'] is None for r in f['branch_relations']))

    def test_tiaohou_scope_and_presence(self):
        r=review_chart(self.c,'yu-chuntai')['method_results'][0]['rules'][0]['finding']
        self.assertTrue(r['applicable'])
        self.assertEqual(r['requested_stems']['甲']['visible'],['年柱'])
        self.assertEqual(r['requested_stems']['丙'],{'visible':[],'hidden':[]})

    def test_tiaohou_rule_does_not_apply_to_other_days(self):
        self.c['central']['pillars'][2]='丁亥'
        f=review_chart(self.c,'yu-chuntai')['method_results'][0]['rules'][0]['finding']
        self.assertFalse(f['applicable'])
        self.assertEqual(f['requested_stems'],{})

    def test_candidate_charts_and_time_conventions_survive(self):
        c=chart('2014-11-13T15:16:00+08:00','female',117.03,'apparent',uncertainty=20)
        r=review_chart(c)
        self.assertTrue(r['ambiguous_chart'])
        self.assertEqual({f['pillars'][3] for f in r['candidate_facts']},{'己未','庚申'})
        self.assertEqual(r['time_conventions_inherited'],c['conventions'])

    def test_no_voting_or_probability(self):
        r=review_chart(self.c)
        self.assertEqual(len(r['method_results']),15)
        self.assertFalse(r['comparison']['majority_vote'])
        self.assertIsNone(r['comparison']['prediction_probability'])

    def test_selection_supports_author_names_and_deduplicates(self):
        r=load_registry()
        self.assertEqual([p['id'] for p in select_profiles('沈孝瞻,shen-xiaozhan,任铁樵',r)],['shen-xiaozhan','ren-tieqiao'])
        for value in ['unknown','','all,shen-xiaozhan']:
            with self.subTest(value=value),self.assertRaises(ValueError):select_profiles(value,r)

    def test_invalid_pillars_rejected(self):
        for p in [[],['甲丑','乙亥','戊子','庚申'],['甲午','乙亥','wrong','庚申']]:
            with self.subTest(p=p),self.assertRaises(ValueError):facts(p)

    def test_unknown_rule_action_rejected(self):
        with self.assertRaises(ValueError):inspect_rule({'action':'unknown'},facts(self.c['central']['pillars']))

    def test_cli_methods_does_not_change_chart(self):
        a=cli('--birth','2014-11-13T15:16:00+08:00','--gender','female')
        b=cli('--birth','2014-11-13T15:16:00+08:00','--gender','female','--methods','all')
        self.assertEqual(b.returncode,0,b.stderr)
        x,y=json.loads(a.stdout),json.loads(b.stdout)
        self.assertEqual(x['central'],y['central'])
        self.assertEqual(y['method_comparison']['methods_version'],'2.3.0-local')
        self.assertEqual(len(y['method_comparison']['method_results']),15)

    def test_cli_unknown_method_is_friendly_error(self):
        r=cli('--birth','2014-11-13T15:16:00+08:00','--methods','unknown')
        self.assertEqual(r.returncode,2)
        self.assertNotIn('Traceback',r.stderr)

    def test_method_list_cli(self):
        r=subprocess.run([sys.executable,'-B','-X','utf8',str(ROOT/'scripts/methods.py'),'--list'],capture_output=True,encoding='utf-8')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual({p['id'] for p in json.loads(r.stdout)},EXPECTED)


if __name__=='__main__':unittest.main()
