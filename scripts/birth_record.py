"""Validate birth records and resolve civil clocks using pinned offline IANA data."""
from datetime import datetime, timezone
import json
import math
import re
from pathlib import Path
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VENDOR = Path(__file__).parent/'vendor'
sys.path.insert(0, str(VENDOR))
import tzdata


def zone(name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_+.-]+(?:/[A-Za-z0-9_+.-]+)*', name) or any(p in ('.', '..') for p in name.split('/')):
        raise ValueError('Invalid IANA timezone name.')
    file = VENDOR/'tzdata/zoneinfo'/name
    try:
        with file.open('rb') as stream:
            return ZoneInfo.from_file(stream, key=name)
    except (OSError, ValueError) as error:
        raise ValueError('Unknown bundled IANA timezone: '+name) from error


def resolve_birth(value, timezone_name=None, fold=None):
    try:
        dt = datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError('Birth must be an ISO date and time.') from error
    if fold is not None and (type(fold) is not int or fold not in (0, 1)):
        raise ValueError('fold must be 0 or 1.')
    if not timezone_name:
        if dt.utcoffset() is None:
            raise ValueError('Birth requires a historical UTC offset or an IANA timezone.')
        if fold is not None:
            raise ValueError('fold requires an IANA timezone.')
        return dt.isoformat(), {'source': 'caller_explicit_offset', 'timezone': None}
    tz = zone(timezone_name)
    naive = dt.replace(tzinfo=None)
    candidates = []
    for f in (0, 1):
        test = naive.replace(tzinfo=tz, fold=f)
        if test.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) == naive:
            if all(test.utcoffset() != c.utcoffset() for c in candidates):
                candidates.append(test)
    if not candidates:
        raise ValueError('This civil time does not exist because the clock moved forward.')
    if dt.utcoffset() is not None:
        matches = [c for c in candidates if c.utcoffset() == dt.utcoffset()]
        if not matches:
            raise ValueError('Explicit UTC offset conflicts with the bundled timezone history.')
        selected = matches[0]
        if fold is not None and selected.fold != fold and len(candidates) > 1:
            raise ValueError('Explicit offset and fold conflict.')
    else:
        if len(candidates) > 1 and fold is None:
            raise ValueError('Ambiguous civil time: choose fold=0 (first) or fold=1 (second).')
        selected = next((c for c in candidates if c.fold == fold), candidates[0])
    return selected.isoformat(), {'source': 'bundled_iana', 'timezone': timezone_name,
                                 'tzdata_version': tzdata.__version__, 'iana_version': tzdata.IANA_VERSION,
                                 'fold': selected.fold, 'offset_seconds': selected.utcoffset().total_seconds()}


def load_record(path):
    try:
        record = json.loads(sys.stdin.read() if path == '-' else Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as error:
        raise ValueError('Cannot read birth-record JSON: '+str(error)) from error
    return validate_record(record)


def validate_record(record):
    if isinstance(record,dict): record = dict(record)
    allowed = {'schema_version', 'birth', 'timezone', 'fold', 'gender', 'uncertainty_minutes',
               'time_source', 'place', 'longitude', 'longitude_source', 'clock', 'day_rule',
               'ziwei_leap', 'ziwei_day_rule', 'sihua_profile'}
    if not isinstance(record, dict) or type(record.get('schema_version')) is not int or record.get('schema_version') != 1 or set(record)-allowed:
        raise ValueError('Birth-record schema_version must be 1; unknown fields are not allowed.')
    birth, evidence = resolve_birth(record.get('birth'), record.get('timezone'), record.get('fold'))
    if record.get('time_source', 'unknown') not in ('birth_certificate', 'hospital_record', 'family_memory', 'unknown'):
        raise ValueError('Unsupported time_source.')
    choices={'gender':('male','female'),'clock':('standard','mean','apparent'),
             'day_rule':('midnight','23','early-late'),'ziwei_day_rule':('next-day','current-day'),
             'ziwei_leap':('all','split','prev-month','next-month','origin-month'),
             'sihua_profile':('iztro','quanshu')}
    for field, values in choices.items():
        if field in record and record[field] not in values: raise ValueError('Unsupported '+field)
    uncertainty=record.get('uncertainty_minutes')
    if uncertainty is not None and (type(uncertainty) is not int or not 0 <= uncertainty <= 120):
        raise ValueError('uncertainty_minutes must be null or an integer from 0 to 120.')
    if 'longitude' in record and (type(record['longitude']) not in (int,float) or not math.isfinite(record['longitude']) or not -180 <= record['longitude'] <= 180):
        raise ValueError('longitude must be a finite number between -180 and 180.')
    for field in ('place', 'longitude_source'):
        if field in record and (not isinstance(record[field], str) or len(record[field]) > 500):
            raise ValueError('Invalid '+field)
    record['birth'] = birth
    record['timezone_evidence'] = evidence
    return record
