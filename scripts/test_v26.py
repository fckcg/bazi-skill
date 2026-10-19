from copy import deepcopy
from datetime import datetime, timedelta, timezone
import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import threading
import unittest
from unittest.mock import patch

from birth_record import resolve_birth, validate_record
from chart import chart, lunar_at, solar_datetime
from solar_time import equation_of_time
from ziwei_bridge import compare, run_engine
from ziwei_reference import audit
import study

NODE = os.environ.get('BAZI_NODE') or shutil.which('node')
ROOT = Path(__file__).resolve().parent.parent


class BirthAndTimeTests(unittest.TestCase):
    def test_unknown_and_explicit_zero_differ(self):
        unknown=chart('2014-11-13T15:16:00+08:00')
        exact=chart('2014-11-13T15:16:00+08:00',uncertainty=0)
        self.assertIsNone(unknown['conventions']['uncertainty_minutes'])
        self.assertIsNone(unknown['stability_confirmed_for_reported_range'])
        self.assertTrue(exact['stability_confirmed_for_reported_range'])
        self.assertEqual(unknown['central']['pillars'],exact['central']['pillars'])

    def test_timezone_dst_and_explicit_conflict(self):
        value,evidence=resolve_birth('1990-07-01T15:10:00','Asia/Shanghai')
        self.assertTrue(value.endswith('+09:00'))
        self.assertEqual(evidence['source'],'bundled_iana')
        with self.assertRaises(ValueError): resolve_birth('1990-07-01T15:10:00+08:00','Asia/Shanghai')

    def test_ambiguous_and_nonexistent_times(self):
        with self.assertRaises(ValueError): resolve_birth('2024-03-10T02:30:00','America/New_York')
        with self.assertRaises(ValueError): resolve_birth('2024-11-03T01:30:00','America/New_York')
        a,_=resolve_birth('2024-11-03T01:30:00','America/New_York',0)
        b,_=resolve_birth('2024-11-03T01:30:00','America/New_York',1)
        self.assertEqual((datetime.fromisoformat(b)-datetime.fromisoformat(a)).total_seconds(),3600)

    def test_record_rejects_unrecognized_and_unsafe_fields(self):
        base={'schema_version':1,'birth':'2014-11-13T15:16:00+08:00'}
        for changes in ({'schema_version':True},{'name':'unneeded'},{'time_source':'verified-by-master'}):
            with self.assertRaises(ValueError): validate_record({**base,**changes})
        for tz in ('../UTC','C:/Windows','Asia\\Shanghai'):
            with self.assertRaises(ValueError): resolve_birth('2014-11-13T15:16:00',tz)

    def test_birth_record_stdin_cli_preserves_quality(self):
        record={'schema_version':1,'birth':'2014-11-13T15:16:00','timezone':'Asia/Shanghai',
                'gender':'female','time_source':'birth_certificate','uncertainty_minutes':None,
                'place':'example county','longitude':116.36,'longitude_source':'county estimate'}
        result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/chart.py'),'--record','-'],
                              input=json.dumps(record),capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        output=json.loads(result.stdout)
        self.assertEqual(output['input']['time_source'],'birth_certificate')
        self.assertEqual(output['input']['timezone_evidence']['timezone'],'Asia/Shanghai')
        self.assertIsNone(output['conventions']['uncertainty_minutes'])

    def test_noaa_120_cross_language_fixtures(self):
        fixture=json.loads((ROOT/'references/solar-fixtures.json').read_text(encoding='utf-8'))
        self.assertEqual(len(fixture['rows']),120)
        for row in fixture['rows']:
            self.assertAlmostEqual(equation_of_time(datetime.fromisoformat(row['utc'])),row['equation_minutes'],places=9)

    def test_equation_of_time_uses_actual_instant(self):
        a=datetime.fromisoformat('2014-11-13T15:16:00+08:00')
        self.assertEqual(equation_of_time(a),equation_of_time(a.astimezone(timezone.utc)))
        with self.assertRaises(ValueError): equation_of_time(datetime(2014,11,13))

    def test_qiyun_segments_split_at_jie(self):
        boundary=solar_datetime(lunar_at(datetime(2014,11,7)).getJieQiTable()['立冬'])
        c=chart(boundary.isoformat(),'female',uncertainty=1)
        self.assertEqual(len(c['qiyun_segments']),2)
        left,right=c['qiyun_segments']
        self.assertEqual(left['birth_end'],right['birth_start'])
        self.assertFalse(left['end_inclusive'])
        self.assertTrue(right['end_inclusive'])
        self.assertNotEqual(left['end_probe']['target_jie'],right['start_probe']['target_jie'])

    def test_more_official_minutes(self):
        from test_official_calendar import engine_table
        fixture=json.loads((ROOT/'references/calendar-extra-fixtures.json').read_text(encoding='utf-8'))
        self.assertEqual(len(fixture['naoj_times']),144)
        for row in fixture['naoj_times']:
            self.assertLessEqual(abs((engine_table(row['year'])[row['term']]-datetime.fromisoformat(row['beijing_time'])).total_seconds()),90)


@unittest.skipUnless(NODE,'Node is required for independent ziwei comparison')
class IndependentZiweiTests(unittest.TestCase):
    def test_engine_fails_on_unknown_five_elements_class(self):
        from ziwei_bridge import ROOT as ZROOT
        result=subprocess.run([NODE,str(ZROOT/'engine.cjs'),'--self-test'],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(json.loads(result.stdout)['unknownClassRejected'])

    def test_240_cross_year_gender_and_hour_cases(self):
        requests=[]
        for year in range(2000,2010):
            for hour in range(12):
                for gender in ('male','female'):
                    requests.append({'birthInfo':{'year':year,'month':11,'day':10,'hour':hour,'gender':gender},'leapMonth':'split'})
        for start in range(0,len(requests),64):
            batch=requests[start:start+64]
            for request,c in zip(batch,run_engine(batch)):
                checked=audit(c,'split')
                self.assertTrue(checked['matches'],(request,checked['differences']))

    def test_sihua_profiles_are_distinct_and_do_not_leak(self):
        base={'birthInfo':{'year':2012,'month':11,'day':10,'hour':8,'gender':'female'},'leapMonth':'split'}
        rows=run_engine([{**base,'sihuaProfile':p} for p in ('iztro','quanshu','iztro')])
        si=lambda c:{s['siHua']:s['name'] for p in c['palaces'] for s in p['stars'] if s.get('siHua')}
        self.assertEqual(si(rows[0])['科'],'左辅')
        self.assertEqual(si(rows[1])['科'],'天府')
        self.assertEqual(si(rows[0]),si(rows[2]))
        self.assertTrue(audit(rows[1],'split','quanshu')['matches'])

    def test_independent_checker_detects_corrupt_star(self):
        z=compare(chart('2014-11-13T15:16:00+08:00'),'female','split')
        c=deepcopy(z['variants'][0]['central']['chart'])
        palace=next(p for p in c['palaces'] if any(s['name']=='太阴' for s in p['stars']))
        star=next(s for s in palace['stars'] if s['name']=='太阴');palace['stars'].remove(star)
        next(p for p in c['palaces'] if p['branch']!=(palace['branch'])).get('stars').append(star)
        self.assertFalse(audit(c,'split')['matches'])


class StudyTests(unittest.TestCase):
    def setUp(self):
        self.temp_base=(Path.cwd()/'.test-artifacts').resolve()
        self.root=self.temp_base/uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.plan={'mode':'retrospective','split':'holdout','subjects':['A','B'],'years':[2020,2021],
                   'categories':['residence_change'],'definitions':{'residence_change':'Primary residence moved to a different city for at least six months; documented records required.'},
                   'rules_version':'test-v1','engine_version':'test-v1','threshold':0.5,
                   'prediction_cutoff':'2026-01-01T00:00:00+00:00'}
        self.truth=[{'subject_id':sid,'year':year,'category':'residence_change','outcome':outcome}
                    for (sid,year),outcome in zip([('A',2020),('A',2021),('B',2020),('B',2021)],[1,0,1,None])]
        self.pred={'model':[{**{k:v for k,v in row.items() if k!='outcome'},'probability':p}
                            for row,p in zip(self.truth,[0.9,0.9,0.2,0.3])],
                   'age_background_baseline':[{**{k:v for k,v in row.items() if k!='outcome'},'probability':0.5} for row in self.truth]}

    def tearDown(self):
        self.assertEqual(self.root.resolve().parent,self.temp_base)
        shutil.rmtree(self.root)

    def ready(self):
        study.init(self.root,self.plan);study.commit_truth(self.root,self.truth);study.register(self.root,self.pred)

    def test_scores_include_false_positives_misses_and_unverifiable(self):
        self.ready(); score=study.evaluate(self.root)['scores']['model']
        self.assertEqual([score[k] for k in ('tp','fp','fn','tn')],[1,1,1,0])
        self.assertEqual(score['unverifiable_slots'],1)
        self.assertAlmostEqual(score['brier'],(0.01+0.81+0.64)/3)
        self.assertEqual(score['precision'],0.5)

    def test_no_overwrite_and_no_partial_predictions(self):
        self.ready()
        with self.assertRaises(ValueError): study.register(self.root,self.pred)
        with self.assertRaises(ValueError): study.rows(self.pred['model'][:-1],study.read(self.root/'manifest.json'),'probability')

    def test_truth_and_predictions_tampering_detected(self):
        self.ready();path=self.root/'registration.json';original=path.read_text(encoding='utf-8')
        changed=json.loads(original);changed['predictions']['model'][0]['probability']=0.1
        path.write_text(json.dumps(changed),encoding='utf-8')
        with self.assertRaises(ValueError): study.evaluate(self.root)
        path.write_text(original,encoding='utf-8')
        truth=self.root/'private/truth.json';changed=study.read(truth);changed['observations'][0]['outcome']=0
        truth.write_text(json.dumps(changed),encoding='utf-8')
        with self.assertRaises(ValueError): study.evaluate(self.root)

    def test_public_input_does_not_read_truth(self):
        self.ready()
        original=study.read; accessed=[]
        def spy(path): accessed.append(str(path));return original(path)
        with patch('study.read',side_effect=spy): result=study.public_input(self.root)
        self.assertFalse(any('private' in path for path in accessed))
        self.assertNotIn('observations',json.dumps(result))

    def test_retrospective_truth_must_precede_registration(self):
        study.init(self.root,self.plan)
        with self.assertRaises(ValueError): study.register(self.root,self.pred)

    def test_baseline_and_explicit_definitions_required(self):
        p=deepcopy(self.plan);p['definitions']['residence_change']='changes'
        with self.assertRaises(ValueError): study.init(self.root,p)
        study.init(self.root,self.plan);study.commit_truth(self.root,self.truth)
        with self.assertRaises(ValueError): study.register(self.root,{'model':self.pred['model']})

    def test_prospective_cutoff_and_order(self):
        start=datetime(2026,1,1,tzinfo=timezone.utc)
        self.plan.update(mode='prospective',years=[2027],prediction_cutoff='2026-12-31T00:00:00+00:00')
        self.plan['subjects']=['A']
        truth=[{'subject_id':'A','year':2027,'category':'residence_change','outcome':1}]
        pred={key:[{'subject_id':'A','year':2027,'category':'residence_change','probability':0.5}] for key in ('model','age_background_baseline')}
        with patch('study.now',return_value=start):
            study.init(self.root,self.plan)
            with self.assertRaises(ValueError):study.commit_truth(self.root,truth)
            study.register(self.root,pred)
            with self.assertRaises(ValueError):study.commit_truth(self.root,truth)
        with patch('study.now',return_value=datetime(2028,1,1,tzinfo=timezone.utc)):
            study.commit_truth(self.root,truth)
            self.assertEqual(study.evaluate(self.root)['mode'],'prospective')


class LocalFormTests(unittest.TestCase):
    def test_local_form_roundtrip_and_cross_origin_rejection(self):
        from http.server import ThreadingHTTPServer
        from local_app import Handler
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=30)
            client.request('GET','/');response=client.getresponse();self.assertEqual(response.status,200);response.read()
            body=json.dumps({'record':{'schema_version':1,'birth':'2014-11-13T15:16:00','timezone':'Asia/Shanghai'},'ziwei':False})
            client.request('POST','/api/chart',body,{'Content-Type':'application/json','Origin':'https://other.invalid'})
            response=client.getresponse();self.assertEqual(response.status,403);response.read()
            client.request('POST','/api/chart',body,{'Content-Type':'application/json','Origin':f'http://127.0.0.1:{server.server_port}'})
            response=client.getresponse();data=json.loads(response.read());self.assertEqual(response.status,200,data)
            self.assertEqual(data['result']['central']['pillars'],['甲午','乙亥','戊子','庚申'])
            client.close()
        finally: server.shutdown();server.server_close();worker.join(timeout=3)


if __name__ == '__main__': unittest.main()
