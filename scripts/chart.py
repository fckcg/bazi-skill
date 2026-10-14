"""Deterministic chart calculation; no event or health predictions."""
import argparse
import calendar
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / 'vendor'))
from lunar_python import Solar

VERSION = '2.1.0-local'
GAN = '甲乙丙丁戊己庚辛壬癸'
ZHI = '子丑寅卯辰巳午未申酉戌亥'
CST = timezone(timedelta(hours=8))


def lunar_at(dt):
    return Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second).getLunar()


def solar_datetime(s):
    return datetime(s.getYear(), s.getMonth(), s.getDay(), s.getHour(), s.getMinute(), s.getSecond(), tzinfo=CST)


def equation_of_time(utc):
    """NOAA fractional-year approximation, minutes; not precision ephemeris."""
    days = 366 if calendar.isleap(utc.year) else 365
    hour = utc.hour + utc.minute / 60 + utc.second / 3600
    g = 2 * math.pi / days * (utc.timetuple().tm_yday - 1 + (hour - 12) / 24)
    return 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                     - 0.014615 * math.cos(2*g) - 0.040849 * math.sin(2*g))


def add_years(dt, years):
    year = dt.year + years
    return dt.replace(year=year, day=min(dt.day, calendar.monthrange(year, dt.month)[1]))


def calculate(dt, gender, longitude, clock='standard', day_rule='early-late'):
    standard = dt.astimezone(CST)
    utc = dt.astimezone(timezone.utc)
    longitude_delta = (longitude - 120) * 4 if longitude is not None else None
    eot = equation_of_time(utc)
    if clock != 'standard' and longitude is None:
        raise ValueError('Solar time requires an explicit longitude.')
    correction = 0 if clock == 'standard' else longitude_delta
    if clock == 'apparent':
        correction += eot
    # Solar clock is represented as wall time; it is not a new civil time zone.
    wall = (standard + timedelta(minutes=correction)).replace(tzinfo=None)
    actual_lunar = lunar_at(standard)
    wall_lunar = lunar_at(wall)
    ec = actual_lunar.getEightChar()
    day_date = wall.date() + timedelta(days=1 if day_rule == '23' and wall.hour == 23 else 0)
    index = (10 + (day_date - datetime(1900, 1, 1).date()).days) % 60
    day = GAN[index % 10] + ZHI[index % 12]
    hour_zhi = ((wall.hour + 1) // 2) % 12
    hour_day = (index + 1) % 60 if day_rule == 'early-late' and wall.hour == 23 else index
    time = GAN[((hour_day % 10 % 5) * 2 + hour_zhi) % 10] + ZHI[hour_zhi]
    pillars = [ec.getYear(), ec.getMonth(), day, time]
    result = {
        'civil_time': dt.isoformat(), 'beijing_time': standard.isoformat(),
        'selected_wall_clock': wall.isoformat(), 'pillars': pillars,
        'lunar_date': actual_lunar.toString(),
        'selected_wall_clock_lunar_date': wall_lunar.toString(),
        'longitude_correction_minutes': longitude_delta,
        'equation_of_time_minutes_approx': round(eot, 4),
        'applied_correction_minutes': round(correction, 4),
    }
    if gender is not None:
        yun = ec.getYun(1 if gender == 'male' else 0, 2)
        target = actual_lunar.getNextJie() if yun.isForward() else actual_lunar.getPrevJie()
        start = solar_datetime(yun.getStartSolar())
        # Dates are traditional convention outputs, not measured future events.
        result['yun'] = {
            'direction': 'forward' if yun.isForward() else 'reverse',
            'target_jie': target.getName(),
            'target_jie_beijing': solar_datetime(target.getSolar()).isoformat(),
            'start_age': {'years': yun.getStartYear(), 'months': yun.getStartMonth(),
                          'days': yun.getStartDay(), 'hours': yun.getStartHour()},
            'start_civil_time': start.astimezone(dt.tzinfo).isoformat(),
            'sequence': [{'ganzhi': d.getGanZhi(),
                          'start': add_years(start, (d.getIndex()-1)*10).astimezone(dt.tzinfo).isoformat(),
                          'end_exclusive': add_years(start, d.getIndex()*10).astimezone(dt.tzinfo).isoformat()}
                         for d in yun.getDaYun(9)[1:]],
        }
    return result


def chart(birth, gender=None, longitude=None, clock='standard', day_rule='early-late', uncertainty=0):
    dt = datetime.fromisoformat(birth)
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('Birth time must include its historical UTC offset, e.g. +08:00.')
    if not 1950 <= dt.year <= 2050:
        raise ValueError('Supported birth years: 1950–2050; other years need separate verification.')
    if gender not in (None, 'male', 'female') or clock not in ('standard', 'mean', 'apparent') or day_rule not in ('midnight', '23', 'early-late'):
        raise ValueError('Unsupported gender, clock or day rule.')
    if longitude is not None and (not math.isfinite(longitude) or not -180 <= longitude <= 180):
        raise ValueError('Longitude must be between -180 and 180.')
    if clock != 'standard' and longitude is None:
        raise ValueError('Solar time requires an explicit longitude.')
    if not isinstance(uncertainty, int) or not 0 <= uncertainty <= 120:
        raise ValueError('Uncertainty must be an integer from 0 to 120 minutes.')
    radius = uncertainty * 60
    # Conservative allowance for the approximate EoT formula near hour/day boundaries.
    scan_radius = radius + (60 if clock == 'apparent' else 0)
    candidates = {}
    start_times = []
    offsets = set(range(-scan_radius, scan_radius + 1, 60)) | {-scan_radius, scan_radius, -radius, radius, 0}
    for term in lunar_at(dt.astimezone(CST)).getJieQiTable().values():
        delta = (solar_datetime(term) - dt).total_seconds()
        if -scan_radius <= delta <= scan_radius:
            offsets.update(int(delta) + n for n in (-1, 0, 1) if -scan_radius <= int(delta) + n <= scan_radius)
    # Explicitly locate solar-clock hour crossings; sampling alone can miss
    # a short-lived combination between a solar term and an hour boundary.
    def hour_bucket(offset):
        sample = dt + timedelta(seconds=offset)
        base = sample.astimezone(CST).replace(tzinfo=None)
        adjustment = 0 if clock == 'standard' else (longitude - 120)*4
        if clock == 'apparent':
            adjustment += equation_of_time(sample.astimezone(timezone.utc))
        wall = base + timedelta(minutes=adjustment)
        return wall.date().toordinal()*24 + wall.hour
    ordered = sorted(offsets)
    for left, right in zip(ordered, ordered[1:]):
        if hour_bucket(left) != hour_bucket(right):
            low, high = left, right
            while high-low > 1:
                mid = (low+high)//2
                if hour_bucket(mid) == hour_bucket(left):
                    low = mid
                else:
                    high = mid
            offsets.update((low, high))
    for offset in sorted(offsets):
        sample = calculate(dt + timedelta(seconds=offset), gender, longitude, clock, day_rule)
        key = tuple(sample['pillars'])
        if key not in candidates:
            candidates[key] = {'pillars': sample['pillars'], 'example_civil_time': sample['civil_time']}
        if gender is not None and offset in (-radius, radius):
            start_times.append(sample['yun']['start_civil_time'])
    central = calculate(dt, gender, longitude, clock, day_rule)
    warnings = ['Traditional interpretations are not validated event predictions.',
                'Historical UTC offset is supplied by the caller; DST is not inferred.',
                'Year/month and qiyun use the actual instant in UTC+8; solar clock affects day/hour only.',
                'Official comparison: 1950–2050 dates (2423/2424 agree; 1979 Dahan midnight difference), 2010–2027 times (432 checked, maximum observed difference 31 seconds). Other exact times are not fully verified.']
    if clock == 'apparent':
        warnings.append('Equation of time uses an approximation; candidate scan includes an extra ±60 seconds. This is an engineering allowance, not a certified error bound.')
    near_terms = []
    for name, term in lunar_at(dt.astimezone(CST)).getJieQiTable().items():
        delta = (solar_datetime(term)-dt).total_seconds()
        if abs(delta) <= radius + 120:
            near_terms.append({'term': name, 'beijing_time': solar_datetime(term).isoformat(),
                               'delta_seconds_from_reported_birth': delta})
    if near_terms:
        warnings.append('Birth range is within 120 seconds of a computed solar term. Verify its authoritative time before confirming year/month or qiyun; 120 seconds is a review threshold, not a certified error bound.')
    return {
        'version': VERSION, 'engine': 'lunar_python==1.4.8',
        'conventions': {'clock': clock, 'day_rule': day_rule, 'qiyun': 'minute-based sect=2',
                        'longitude': longitude, 'uncertainty_minutes': uncertainty},
        'central': central, 'pillars_stable_in_scanned_range': len(candidates) == 1,
        'candidates': list(candidates.values()), 'qiyun_endpoint_results': start_times,
        'near_solar_terms_requiring_review': near_terms,
        'warnings': warnings,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--birth', required=True, help='ISO local civil timestamp with historical UTC offset')
    p.add_argument('--gender', choices=['male', 'female'])
    p.add_argument('--longitude', type=float)
    p.add_argument('--clock', choices=['standard', 'mean', 'apparent'], default='standard')
    p.add_argument('--day-rule', choices=['midnight', '23', 'early-late'], default='early-late')
    p.add_argument('--uncertainty', type=int, default=0, help='± minutes; 0 means reported exact')
    a = p.parse_args()
    try:
        result = chart(a.birth, a.gender, a.longitude, a.clock, a.day_rule, a.uncertainty)
    except ValueError as e:
        p.error(str(e))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
