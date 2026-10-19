"""Local preregistration and blinded-evaluation helper; no predictions are generated.

Local hashes detect accidental edits, not a malicious editor or dishonest clock.
Use a separate evaluator and independent timestamp for stronger evidence.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import secrets

CATEGORIES = {'education_change', 'residence_change', 'job_change', 'relationship_change'}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise ValueError('Cannot read study JSON: '+str(error)) from error


def write_once(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    except FileExistsError as error:
        raise ValueError('Registration already exists; create a new study instead of overwriting.') from error


def now():
    return datetime.now(timezone.utc)


def stamp(value):
    try:
        result = datetime.fromisoformat(value)
        if result.utcoffset() is None: raise ValueError()
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError) as error:
        raise ValueError('Cutoff must have an explicit UTC offset.') from error


def init(root, plan):
    allowed = {'mode','split','subjects','years','categories','definitions','rules_version','engine_version',
               'threshold','prediction_cutoff'}
    if not isinstance(plan, dict) or set(plan) != allowed:
        raise ValueError('Plan fields must match the documented schema exactly.')
    if plan['mode'] not in ('retrospective','prospective') or plan['split'] not in ('development','holdout'):
        raise ValueError('Explicit study mode and dataset split required.')
    subjects = plan['subjects']
    if not isinstance(subjects,list) or not subjects or any(not isinstance(s,str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',s) for s in subjects) or len(set(subjects)) != len(subjects):
        raise ValueError('Use unique pseudonymous subject ids.')
    for key in ('rules_version','engine_version'):
        if not isinstance(plan[key],str) or not plan[key].strip(): raise ValueError('Missing '+key)
    years, cats = plan['years'], plan['categories']
    if not isinstance(years,list) or not years or any(type(y) is not int or not 1900 <= y <= 2200 for y in years) or len(set(years)) != len(years):
        raise ValueError('Years must be a unique integer list.')
    if not isinstance(cats,list) or not cats or any(c not in CATEGORIES for c in cats) or len(set(cats)) != len(cats):
        raise ValueError('Use the documented concrete event categories.')
    if not isinstance(plan['definitions'],dict) or set(plan['definitions']) != set(cats) or any(not isinstance(t,str) or len(t.strip()) < 20 for t in plan['definitions'].values()):
        raise ValueError('Each event needs an explicit definition, exclusions and evidence standard.')
    if type(plan['threshold']) not in (int,float) or not 0 < plan['threshold'] < 1:
        raise ValueError('Threshold must be between zero and one.')
    cutoff = stamp(plan['prediction_cutoff'])
    if plan['mode'] == 'prospective' and (cutoff <= now() or min(years) < cutoff.year):
        raise ValueError('Prospective registration must precede cutoff and its target years.')
    if plan['mode'] == 'retrospective' and max(years) >= now().year:
        raise ValueError('Retrospective study uses completed calendar years.')
    if len(subjects)*len(years)*len(cats) > 10000: raise ValueError('Study exceeds 10000 observation slots.')
    manifest = {**plan,'schema_version':1,'created_at':now().isoformat(),
                'timestamp_trust':'local_clock_not_independently_attested'}
    write_once(Path(root)/'manifest.json',manifest)
    return manifest


def slots(manifest):
    return set(itertools.product(manifest['subjects'],manifest['years'],manifest['categories']))


def rows(value, manifest, field):
    if not isinstance(value,list): raise ValueError('Observations/predictions must be lists.')
    output = {}; expected_slots = slots(manifest)
    for row in value:
        if not isinstance(row,dict) or set(row) != {'subject_id','year','category',field}:
            raise ValueError('Each row must contain subject_id/year/category/'+field)
        key = (row['subject_id'],row['year'],row['category'])
        if type(row['year']) is not int or key not in expected_slots or key in output:
            raise ValueError('Duplicate or out-of-scope observation slot.')
        v = row[field]
        if field == 'probability':
            if type(v) not in (int,float) or not math.isfinite(v) or not 0 <= v <= 1:
                raise ValueError('Every probability must be finite and between zero and one.')
        elif v is not None and (type(v) is not int or v not in (0,1)):
            raise ValueError('Outcome is 0/1; null means unverifiable, not a miss.')
        output[key] = v
    if set(output) != expected_slots: raise ValueError('Every predefined slot must be present; no selective omissions.')
    return output


def commit_truth(root, observations):
    root = Path(root)
    manifest = read(root/'manifest.json')
    checked = rows(observations,manifest,'outcome')
    if manifest['mode'] == 'retrospective' and (root/'registration.json').exists():
        raise ValueError('Retrospective truth must be committed before predictions.')
    if manifest['mode'] == 'prospective' and not (root/'registration.json').exists():
        raise ValueError('Register prospective predictions before supplying outcomes.')
    for (_, year, _), outcome in checked.items():
        if outcome is not None and (year > now().year or year == now().year and outcome == 0):
            raise ValueError('Future/uncompleted years cannot be scored as absent events.')
    private = {'salt':secrets.token_hex(32),'observations':observations}
    commitment = {'truth_sha256':digest(private),'manifest_sha256':digest(manifest),'committed_at':now().isoformat()}
    if (root/'truth-commitment.json').exists(): raise ValueError('Truth already committed.')
    write_once(root/'private/truth.json',private)
    write_once(root/'truth-commitment.json',commitment)
    return commitment


def register(root, predictions):
    root = Path(root)
    manifest = read(root/'manifest.json')
    if not isinstance(predictions,dict) or not {'model','age_background_baseline'} <= set(predictions) or set(predictions)-{'model','age_background_baseline','shuffled_chart_baseline'}:
        raise ValueError('Model and age_background_baseline predictions are required; shuffled baseline is optional.')
    if manifest['mode'] == 'retrospective' and not (root/'truth-commitment.json').exists():
        raise ValueError('Commit hidden historical truth before predictions.')
    if manifest['mode'] == 'prospective' and now() >= stamp(manifest['prediction_cutoff']):
        raise ValueError('Prediction cutoff has passed.')
    for predictions_for_model in predictions.values(): rows(predictions_for_model,manifest,'probability')
    registered = {'manifest_sha256':digest(manifest),'registered_at':now().isoformat(),
                  'predictions':predictions,'timestamp_trust':'local_clock_not_independently_attested'}
    write_once(root/'registration.json',registered)
    write_once(root/'registration-sha256.json',{'sha256':digest(registered)})
    return {'sha256':digest(registered),'registered_at':registered['registered_at']}


def public_input(root):
    # Does not load truth.json or its outcome bytes.
    manifest = read(Path(root)/'manifest.json')
    return {'plan':manifest,'instructions':'Use only permitted birth inputs; do not open private outcomes or ask for life events. Record all slots before evaluation.'}


def wilson(success, total):
    if not total: return None
    z=1.95996398454; p=success/total; den=1+z*z/total
    middle=(p+z*z/(2*total))/den
    delta=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/den
    return [max(0,middle-delta),min(1,middle+delta)]


def evaluate(root):
    root=Path(root); manifest=read(root/'manifest.json'); commitment=read(root/'truth-commitment.json')
    truth=read(root/'private/truth.json'); registered=read(root/'registration.json')
    if digest(truth) != commitment['truth_sha256'] or digest(manifest) != commitment['manifest_sha256'] or digest(manifest) != registered['manifest_sha256']:
        raise ValueError('Truth or manifest was changed after commitment.')
    if digest(registered) != read(root/'registration-sha256.json')['sha256']:
        raise ValueError('Registered predictions were changed.')
    outcomes=rows(truth['observations'],manifest,'outcome'); scores={}
    for label, prediction_rows in registered['predictions'].items():
        probabilities=rows(prediction_rows,manifest,'probability')
        observed=[(probabilities[k],v) for k,v in outcomes.items() if v is not None]
        if not observed: raise ValueError('No verifiable outcomes; cannot score.')
        tp=fp=fn=tn=0
        for p,y in observed:
            yes=p >= manifest['threshold']
            tp+=int(yes and y==1);fp+=int(yes and y==0);fn+=int(not yes and y==1);tn+=int(not yes and y==0)
        scores[label]={'observed_slots':len(observed),'unverifiable_slots':len(outcomes)-len(observed),
                       'tp':tp,'fp':fp,'fn':fn,'tn':tn,'precision':tp/(tp+fp) if tp+fp else None,
                       'recall':tp/(tp+fn) if tp+fn else None,'precision_wilson_interval':wilson(tp,tp+fp),
                       'recall_wilson_interval':wilson(tp,tp+fn),
                       'brier':sum((p-y)**2 for p,y in observed)/len(observed)}
    return {'split':manifest['split'],'mode':manifest['mode'],'subjects':len(manifest['subjects']),
            'rules_version':manifest['rules_version'],'scores':scores,
            'model_brier_minus_age_baseline':scores['model']['brier']-scores['age_background_baseline']['brier'],
            'limitations':['Local file/clock integrity is not independent timestamping or proof of blinding.',
                          'Year/category slots for the same person are correlated; Wilson intervals are descriptive, not a causal or clustered validation.',
                          'Development scores do not establish held-out or prospective prediction validity.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['init','commit-truth','register','public-input','evaluate'])
    parser.add_argument('--root',required=True);parser.add_argument('--file')
    args=parser.parse_args()
    try:
        if args.action in ('init','commit-truth','register') and not args.file:
            raise ValueError('This action requires --file JSON.')
        result={'init':lambda:init(args.root,read(args.file)),
                'commit-truth':lambda:commit_truth(args.root,read(args.file)),
                'register':lambda:register(args.root,read(args.file)),
                'public-input':lambda:public_input(args.root),'evaluate':lambda:evaluate(args.root)}[args.action]()
    except (ValueError,KeyError,TypeError,OSError) as error:
        parser.error(str(error))
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__': main()
