"""Offline adapter: a shared, corrected birth clock feeds a separate ziwei engine."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from chart import CST, equation_of_time

ROOT = Path(__file__).resolve().parent / 'ziwei'
POLICIES = ('split', 'prev-month', 'next-month', 'origin-month')
LABELS = {'split': '闰月分半', 'prev-month': '闰月归前月',
          'next-month': '闰月归后月', 'origin-month': '保留闰月，不作分半'}
BRANCHES = '子丑寅卯辰巳午未申酉戌亥'


def wall_clock(dt, clock, longitude):
    correction = 0 if clock == 'standard' else (longitude - 120) * 4
    if clock == 'apparent':
        correction += equation_of_time(dt.astimezone(timezone.utc))
    return (dt.astimezone(CST) + timedelta(minutes=correction)).replace(tzinfo=None)


def prepare_inputs(bazi, gender, day_rule):
    if gender not in ('female', 'male'):
        raise ValueError('紫微排盘需要 --gender female 或 male。')
    if day_rule not in ('current-day', 'next-day'):
        raise ValueError('Unsupported ziwei day rule.')
    dt = datetime.fromisoformat(bazi['central']['civil_time'])
    conv = bazi['conventions']
    radius = (conv['uncertainty_minutes'] or 0) * 60 + (60 if conv['clock'] == 'apparent' else 0)

    def one(offset):
        moment = dt + timedelta(seconds=offset)
        wall = wall_clock(moment, conv['clock'], conv['longitude'])
        date = wall.date() + timedelta(days=int(day_rule == 'next-day' and wall.hour == 23))
        if not 1950 <= date.year <= 2050:
            raise ValueError('紫微候选排盘日超出1950—2050支持范围。')
        birth = {'year': date.year, 'month': date.month, 'day': date.day,
                 'hour': ((wall.hour + 1) // 2) % 12, 'gender': gender}
        key = (date.isoformat(), birth['hour'])
        return key, {'birthInfo': birth, 'example_civil_time': moment.isoformat(),
                     'example_selected_wall_clock': wall.isoformat()}

    central_key, central = one(0)
    candidates = {central_key: central}
    # Scan every second: cheap clock arithmetic, no repeated lunar conversion.
    # This catches date and hour transitions even for sub-minute solar shifts.
    for offset in range(-radius, radius + 1):
        key, sample = one(offset)
        candidates.setdefault(key, sample)
    return list(candidates.values())


def run_engine(requests):
    node = os.environ.get('BAZI_NODE') or shutil.which('node')
    if not node:
        raise ValueError('紫微模块需要 Node.js 18+；安装后重开终端，或用 BAZI_NODE 指定 node.exe。原八字功能不需要 Node.js。')
    bundle = ROOT / 'engine.cjs'
    if not bundle.is_file():
        raise ValueError('紫微离线引擎 engine.cjs 缺失，请使用完整发布包。')
    try:
        manifest = json.loads((ROOT / 'provenance.json').read_text(encoding='utf-8'))
        if not isinstance(manifest, dict):
            raise ValueError('Expected a JSON object.')
    except (OSError, ValueError) as error:
        raise ValueError('紫微来源清单缺失或损坏，请使用完整发布包。') from error
    expected = manifest.get('bundle_sha256')
    if not expected or hashlib.sha256(bundle.read_bytes()).hexdigest() != expected:
        raise ValueError('紫微离线引擎校验失败，请重新构建并更新来源清单。')
    try:
        completed = subprocess.run([node, str(bundle)], input=json.dumps({'requests': requests}),
                                   text=True, encoding='utf-8', capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError('紫微引擎无法运行：' + str(error)) from error
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or '紫微引擎运行失败。')
    try:
        charts = json.loads(completed.stdout)
        if not isinstance(charts, list) or len(charts) != len(requests):
            raise ValueError('Unexpected ziwei response count.')
        for chart in charts:
            if len(chart['palaces']) != 12 or len({p['branch'] for p in chart['palaces']}) != 12:
                raise ValueError('Invalid ziwei palace structure.')
        return charts
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError('紫微引擎返回了无效结构。') from error


def structure_key(chart):
    return json.dumps({k: chart[k] for k in ('palaces', 'mingGongBranch', 'shenGongBranch',
                      'wuxingJu', 'ziweiPos', 'daXians')}, ensure_ascii=False, sort_keys=True)


def compare(bazi, gender, leap_policy='all', day_rule='next-day', sihua_profile='iztro'):
    if leap_policy not in ('all',) + POLICIES:
        raise ValueError('Unsupported ziwei leap-month policy.')
    if sihua_profile not in ('iztro', 'quanshu'):
        raise ValueError('Unsupported sihua profile.')
    samples = prepare_inputs(bazi, gender, day_rule)
    policies = POLICIES if leap_policy == 'all' else (leap_policy,)
    requests = [{'birthInfo': sample['birthInfo'], 'leapMonth': policy, 'sihuaProfile': sihua_profile}
                for policy in policies for sample in samples]
    charts = iter(run_engine(requests))
    variants = []
    for policy in policies:
        candidates = [{**sample, 'chart': next(charts)} for sample in samples]
        from ziwei_reference import audit
        for candidate in candidates:
            candidate['independent_check'] = audit(candidate['chart'], policy, sihua_profile)
        variants.append({'policy': policy, 'label': LABELS[policy],
                         'central': candidates[0], 'candidates': candidates,
                         'structure_stable_in_scanned_range':
                         len({structure_key(c['chart']) for c in candidates}) == 1})
    return {
        'engine': 'Renhuai123/ziwei-doushu adapted subset + iztro==2.5.8',
        'profile': 'classic-table-adapter-v1',
        'source': 'https://github.com/Renhuai123/ziwei-doushu',
        'conventions': {'clock': bazi['conventions']['clock'], 'day_rule': day_rule,
                        'year_rule': 'lunar-new-year', 'leap_policy': leap_policy,
                        'sihua_profile': sihua_profile,
                        'uncertainty_known': bazi['conventions']['uncertainty_minutes'] is not None,
                        'brightness': 'upstream classic table with iztro fallback',
                        'time_correction_applied_once': True,
                        'uncertainty_minutes': bazi['conventions']['uncertainty_minutes']},
        'variants': variants,
        'same_structure_across_selected_policies': len({structure_key(v['central']['chart']) for v in variants}) == 1,
        'warnings': ['紫微按所选钟的日期与时辰排盘；原始出生时间和晚子时换日另行保留。',
                     '四种闰月策略是传统约定，不按往事吻合选定。',
                     '未包含上游商业断语库、AI接口、海量数据集或倪师逐字稿。',
                     '本地经典亮度口径不等同上游当前文墨模式；不是逐星复刻。',
                     '疾厄等宫名是传统术语，不代表健康诊断；两体系一致不代表预测概率。'],
    }


def render_markdown(result):
    b = result['central']
    z = result['ziwei']
    uncertainty = result['conventions']['uncertainty_minutes']
    uncertainty_text = '未知，暂定中央时刻，不能确认全范围稳定' if uncertainty is None else f'±{uncertainty}分钟（按调用参数）'
    lines = ['# 八字与紫微排盘报告', '',
             f"出生记录：{b['civil_time']}；所选钟：{result['conventions']['clock']}；输入误差：{uncertainty_text}。",
             f"所选钟时间：{b['selected_wall_clock']}；农历（实际UTC+8）：{b['lunar_date']}。", '',
             '## 八字', '', '四柱：' + '　'.join(b['pillars']),
             f"换日规则：{result['conventions']['day_rule']}；{'名义扫描内无变化，实际范围未确认' if uncertainty is None else '扫描范围四柱稳定：'+('是' if result['pillars_stable_in_scanned_range'] else '否')}。"]
    if not result['pillars_stable_in_scanned_range']:
        lines += ['', '候选四柱：'] + ['- ' + '　'.join(c['pillars']) for c in result['candidates']]
    if b.get('yun'):
        lines += ['', '大运（传统计算约定）：'] + [f"- {d['ganzhi']}：{d['start']} 至 {d['end_exclusive']}（终点不含）" for d in b['yun']['sequence']]
        if result['conventions']['uncertainty_minutes']:
            lines += ['', '出生时间误差两端对应的起运结果（不是严格起运范围）：']
            lines += ['- ' + value for value in result['qiyun_endpoint_results']]
            lines += ['若误差跨越交节或年界，区间内还可能出现其他起运结果。']
        for segment in result.get('qiyun_segments', []):
            lines += ['', f"起运分段：出生输入{segment['birth_start']}至{segment['birth_end']}（{'包含' if segment['end_inclusive'] else '不含'}右端点）。",
                      f"- 左探针：{segment['start_probe']['target_jie']}；起运{segment['start_probe']['start_civil_time']}",
                      f"- 右探针：{segment['end_probe']['target_jie']}；起运{segment['end_probe']['start_civil_time']}"]
    lines += ['', '## 紫微', '',
              f"换年：农历正月初一；晚子时：{z['conventions']['day_rule']}；亮度：本地经典表口径。",
              '大限下表为传统年龄区间，不直接等同公历年份。']
    for v in z['variants']:
        c = v['central']['chart']
        lines += ['', '### ' + v['label'], '',
                  f"命宫：{BRANCHES[c['mingGongBranch']]}；身宫：{BRANCHES[c['shenGongBranch']]}；{c['wuxingJuName']}；命主：{c['mingZhu']}；身主：{c['shenZhu']}。",
                  f"{'仅名义扫描，实际时间范围未知' if uncertainty is None else '时间范围结构稳定：'+('是' if v['structure_stable_in_scanned_range'] else '否')}；候选输入数：{len(v['candidates'])}。", '',
                  '| 宫位 | 地支 | 主星 | 本命四化 | 大限年龄 |', '|---|---|---|---|---|']
        lunar = c['lunarInfo']
        check = v['central']['independent_check']
        lines.insert(len(lines)-2, '独立公式复核：'+('所列检查一致。' if check['matches'] else '存在差异，需复核，详见JSON。')+'\n')
        if lunar.get('dayClamped'):
            lines.insert(len(lines)-2, f"该规则把原农历{lunar['rawLunarMonth']}月{lunar['rawLunarDay']}日映射为有效{lunar['lunarMonth']}月{lunar['lunarDay']}日（目标月天数截断）；这不改变实际生日。\n")
        for p in c['palaces']:
            major = '、'.join(s['name'] + ('（'+s['brightnessRaw']+'）' if s.get('brightnessRaw') else '')
                             for s in p['stars'] if s['type'] == 'major') or '空宫'
            sihua = '、'.join(s['name']+'化'+s['siHua'] for s in p['stars'] if s.get('siHua')) or '—'
            age = '—' if not p.get('daXianAge') else '—'.join(map(str, p['daXianAge']))
            lines.append(f"| {p['name']} | {BRANCHES[p['branch']]} | {major} | {sihua} | {age} |")
        if not v['structure_stable_in_scanned_range']:
            lines += ['', '边界候选概览（完整星曜差异见JSON）：', '']
            for sample in v['candidates']:
                c = sample['chart']
                lines.append(f"- {sample['example_selected_wall_clock']} → 命宫{BRANCHES[c['mingGongBranch']]}、身宫{BRANCHES[c['shenGongBranch']]}、{c['wuxingJuName']}；排盘输入{json.dumps(sample['birthInfo'], ensure_ascii=False)}")
    lines += ['', '## 并列比较', '',
              '所选闰月规则中央盘结构相同：' + ('是。' if z['same_structure_across_selected_policies'] else '否，应分别保留，不能强行合并。'),
              '八字与紫微使用不同换年月规则；本报告呈现结构，不把星曜或十神直接认定为性格、能力或过去事件。', '',
              '## 计算限制与来源', '']
    translations = [
        ('Traditional interpretations', '传统解读的现实事件预测效度尚未建立。'),
        ('Historical UTC offset', '历史UTC偏移由调用者提供；本程序不自行推断夏令时。'),
        ('Year/month and qiyun', '八字年/月柱与起运按实际UTC+8瞬间；太阳钟只影响八字日/时柱。'),
        ('Official comparison', '八字历法已核对1950—2050节气日期（2424项中2423项一致，保留1979大寒午夜差异）及2004—2027时刻（576项，已观察最大差31秒）；不是紫微全量核验。'),
        ('Equation of time', '均时差采用近似公式；候选扫描额外±60秒为工程余量，不是严格误差上界。'),
        ('Birth range', '出生范围接近计算交节时刻，确认八字年/月柱或起运前需要权威时刻复核。'),
        ('Birth-time uncertainty', '出生时间误差未知；当前候选只覆盖名义时刻与太阳模型工程余量，不能确认实际全范围稳定。'),
    ]
    for warning in result['warnings'] + z['warnings']:
        lines.append('- ' + next((text for prefix, text in translations if warning.startswith(prefix)), warning))
    for term in result['near_solar_terms_requiring_review']:
        lines.append(f"- 待复核交节：{term['term']}，程序时刻{term['beijing_time']}。")
    lines += ['', '[紫微来源](https://github.com/Renhuai123/ziwei-doushu)，适配范围见 scripts/ziwei/provenance.json。']
    return '\n'.join(lines) + '\n'
