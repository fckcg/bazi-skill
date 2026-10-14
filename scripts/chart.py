"""Deterministic chart calculation; no event or health predictions."""
import argparse
import calendar
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / 'vendor'))
from lunar_python import Solar, Lunar

VERSION = '2.3.0-local'
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


def lunar_birth(lunar_date, birth_time, utc_offset, leap=False):
    """Convert a Chinese lunar calendar date; never infer leap month or UTC offset."""
    import re
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", lunar_date):
        raise ValueError('Lunar date must be YYYY-MM-DD with month 01 through 12.')
    year, month, day = map(int, lunar_date.split('-'))
    if not 1950 <= year <= 2050 or not 1 <= month <= 12 or not 1 <= day <= 30:
        raise ValueError('Invalid lunar year, month or day.')
    if not re.fullmatch(r"[0-9]{2}:[0-9]{2}(?::[0-9]{2})?", birth_time):
        raise ValueError('Birth time must be HH:MM or HH:MM:SS.')
    if not re.fullmatch(r"[+-](?:0[0-9]|1[0-4]):[0-5][0-9]", utc_offset):
        raise ValueError('Historical UTC offset must be explicit, e.g. +08:00.')
    try:
        clock = datetime.fromisoformat('2000-01-01T'+birth_time+utc_offset)
    except ValueError as e:
        raise ValueError('Invalid birth time or UTC offset.') from e
    # Explicitly restrict direct lunar input to China/Hong Kong clock conventions.
    # Overseas lunar dates need calendar/location clarification before conversion.
    if clock.utcoffset() not in (timedelta(hours=8), timedelta(hours=9)):
        raise ValueError('Direct lunar input supports +08:00 or historical China DST +09:00. Convert overseas lunar dates separately and use --birth.')
    try:
        lunar = Lunar.fromYmdHms(year, -month if leap else month, day,
                                clock.hour, clock.minute, clock.second)
        solar = lunar.getSolar()
        converted = datetime(solar.getYear(), solar.getMonth(), solar.getDay(),
                             clock.hour, clock.minute, clock.second, tzinfo=clock.tzinfo)
        # Independent round trip ensures the library has not normalized the input.
        check = Solar.fromYmd(solar.getYear(), solar.getMonth(), solar.getDay()).getLunar()
        if (check.getYear(), check.getMonth(), check.getDay()) != (year, -month if leap else month, day):
            raise ValueError('Lunar conversion round trip did not match the input.')
    except Exception as e:
        raise ValueError('Invalid lunar date or nonexistent leap month: '+str(e)) from e
    if not 1950 <= converted.year <= 2050:
        raise ValueError('Converted Gregorian birth year is outside 1950-2050.')
    return converted.isoformat()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    dates = p.add_mutually_exclusive_group(required=True)
    dates.add_argument('--birth', help='ISO local civil timestamp with historical UTC offset')
    dates.add_argument('--lunar-date', help='Chinese lunar date YYYY-MM-DD; month is unsigned')
    p.add_argument('--lunar-leap', action='store_true', help='Explicitly select the leap month')
    p.add_argument('--time', help='Birth clock time HH:MM[:SS], required for lunar input')
    p.add_argument('--utc-offset', help='Historical UTC offset, required for lunar input')
    p.add_argument('--methods', help='Optional source-gated comparison: all or comma-separated author names/ids')
    p.add_argument('--gender', choices=['male', 'female'])
    p.add_argument('--longitude', type=float)
    p.add_argument('--clock', choices=['standard', 'mean', 'apparent'], default='standard')
    p.add_argument('--day-rule', choices=['midnight', '23', 'early-late'], default='early-late')
    p.add_argument('--uncertainty', type=int, default=0, help='± minutes; 0 means reported exact')
    a = p.parse_args()
    try:
        if a.lunar_date:
            if not a.time or not a.utc_offset:
                raise ValueError('Lunar input requires --time and --utc-offset.')
            birth = lunar_birth(a.lunar_date, a.time, a.utc_offset, a.lunar_leap)
        else:
            if a.time or a.utc_offset or a.lunar_leap:
                raise ValueError('--time, --utc-offset and --lunar-leap only apply to --lunar-date.')
            birth = a.birth
        result = chart(birth, a.gender, a.longitude, a.clock, a.day_rule, a.uncertainty)
        result['input'] = {'calendar': 'lunar' if a.lunar_date else 'gregorian',
                           'original_date': a.lunar_date or a.birth,
                           'leap_month': bool(a.lunar_leap) if a.lunar_date else None,
                           'birth_time': a.time, 'historical_utc_offset': a.utc_offset,
                           'converted_gregorian_birth': birth}
        if a.methods:
            from methods import review_chart
            result['method_comparison'] = review_chart(result, a.methods)
    except ValueError as e:
        p.error(str(e))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
