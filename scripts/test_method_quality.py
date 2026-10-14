from copy import deepcopy
import unittest
import json
from pathlib import Path
import subprocess
import sys
from chart import chart
from methods import inspect_rule, load_registry, render_markdown, review_chart, validate_registry


class MethodQualityTests(unittest.TestCase):
    def setUp(self):
        self.c=chart('2014-11-13T15:16:00+08:00','female',117.03,'apparent',uncertainty=20)

    def test_new_author_rules_are_connected(self):
        r=load_registry()
        self.assertEqual(len(r['rules']),10)
        for author in ['chen-suan','wei-qianli','yuan-shushan']:
            p=next(p for p in r['profiles'] if p['id']==author)
            self.assertEqual(p['source_status'],'text_excerpt_checked')
            self.assertTrue(p['verified_rule_ids'])

    def test_rules_are_evaluated_for_every_candidate(self):
        r=review_chart(self.c,'ren-tieqiao,yu-chuntai,wei-qianli')
        roots=r['method_results'][0]['rules'][0]
        self.assertEqual({tuple(x['pillars']) for x in roots['candidate_findings']},{tuple(x['pillars']) for x in self.c['candidates']})
        self.assertFalse(roots['stable_across_candidates'])
        self.assertTrue(r['method_results'][1]['rules'][0]['stable_across_candidates'])

    def test_wei_month_appearance_is_candidate_not_final_format(self):
        r=review_chart(self.c,'wei-qianli')['method_results'][0]
        rule=next(x for x in r['rules'] if x['rule_id']=='WEI-002')
        self.assertEqual(rule['finding']['review_path'],'other_hidden_qi_visible')
        self.assertEqual(rule['finding']['candidate_gods'],[{'stem':'甲','god':'七杀'}])
        self.assertIsNone(rule['finding']['final_format'])

    def test_peer_rule_changes_with_hour_candidate(self):
        r=review_chart(self.c,'wei-qianli')['method_results'][0]['rules'][0]
        self.assertEqual(r['rule_id'],'WEI-001')
        self.assertFalse(r['stable_across_candidates'])
        hidden=[x['finding']['hidden_peers'] for x in r['candidate_findings']]
        self.assertNotEqual(hidden[0],hidden[1])

    def test_seasonal_terms_are_not_personal_risks(self):
        r=review_chart(self.c,'yuan-shushan')['method_results'][0]['rules'][0]['finding']
        self.assertEqual(r['states'],{'水':'旺','木':'相','金':'休','土':'囚','火':'死'})
        c=chart('2014-10-13T15:16:00+08:00')
        r=review_chart(c,'yuan-shushan')['method_results'][0]['rules'][0]['finding']
        self.assertTrue(r['earth_transition_convention_requires_review'])
        self.assertIsNone(r['states'])

    def test_theoretical_disagreement_is_preserved(self):
        r=review_chart(self.c,'chen-suan,ren-tieqiao')
        self.assertEqual(r['comparison']['method_disagreements'][0]['profiles'],['chen-suan','ren-tieqiao'])
        self.assertFalse(r['comparison']['majority_vote'])
        self.assertEqual(review_chart(self.c,'chen-suan')['comparison']['method_disagreements'],[])

    def test_malformed_candidate_data_rejected(self):
        changes=[{'candidates':None},{'candidates':[None]},
                 {'conventions':[]},{'near_solar_terms_requiring_review':{}},
                 {'pillars_stable_in_scanned_range':True},
                 {'pillars_stable_in_scanned_range':'false'},
                 {'candidates':[{'pillars':['甲午','乙亥','丁亥','庚申']}]}]
        for change in changes:
            c=deepcopy(self.c);c.update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):review_chart(c)

    def test_unverified_rule_activation_rejected(self):
        r=load_registry();r=deepcopy(r)
        owner=next(p for p in r['profiles'] if p['id']==r['rules'][0]['profile'])
        owner['source_status']='bibliography_checked'
        with self.assertRaises(ValueError):validate_registry(r)

    def test_missing_or_misattributed_source_rejected(self):
        for field,value in [('source_url','https://example.com/unregistered'),('locator',''),('evidence_status','pending')]:
            r=deepcopy(load_registry());r['rules'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate_registry(r)

    def test_duplicate_and_dangling_registry_ids_rejected(self):
        r=deepcopy(load_registry());r['rules'].append(deepcopy(r['rules'][0]))
        with self.assertRaises(ValueError):validate_registry(r)
        r=deepcopy(load_registry());r['profiles'][0]['verified_rule_ids'].append('missing')
        with self.assertRaises(ValueError):validate_registry(r)

    def test_duplicate_candidates_deduplicated(self):
        c=deepcopy(self.c);c['candidates'].append(deepcopy(c['candidates'][0]))
        r=review_chart(c,'ren-tieqiao')
        self.assertEqual(len(r['candidate_facts']),2)
        self.assertEqual(len(r['method_results'][0]['rules'][0]['candidate_findings']),2)

    def test_readable_output_contains_source_and_candidate_limits(self):
        r=review_chart(self.c,'chen-suan,ren-tieqiao,liang-xiangrun')
        text=render_markdown(r)
        self.assertIn('己未',text);self.assertIn('庚申',text)
        self.assertIn('有差异，不能只采用中央盘',text)
        self.assertIn('具体原文规则尚未核对',text)
        self.assertIn('https://yiology.net/',text)
        self.assertIn('藏干分日',text)

    def test_readable_cli_accepts_stdin(self):
        script=Path(__file__).with_name('methods.py')
        r=subprocess.run([sys.executable,'-B','-X','utf8',str(script),'--chart-json','-',
                          '--select','chen-suan,wei-qianli','--format','markdown'],
                         input=json.dumps(self.c,ensure_ascii=False),capture_output=True,encoding='utf-8')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('陈素庵',r.stdout)
        self.assertIn('月令本气',r.stdout)
        self.assertIn('所列原文段落已核对',r.stdout)


if __name__=='__main__' :unittest.main()
