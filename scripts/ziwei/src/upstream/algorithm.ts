// Adapted from Renhuai123/ziwei-doushu (MIT). See provenance.json.
import { astro } from 'iztro';
import { Solar, LunarMonth } from 'lunar-javascript';
import type { BirthInfo, LunarInfo, Star, Palace, DaXian, DaXianSiHua, ZiweiChart } from './types';
import { BRANCHES, STEMS, SI_HUA_TABLE } from './constants';

const DEFAULT_BRIGHTNESS: Record<string, string[]> = {

    '紫微': ['庙','旺','得','旺','庙','庙','旺','旺','得','旺','平','庙'],

    '天机': ['得','旺','庙','平','庙','陷','得','旺','庙','平','庙','陷'],

    '太阳': ['旺','庙','旺','旺','庙','得','得','陷','不','陷','陷','不'],

    '天同': ['旺','平','平','庙','不','不','旺','平','平','庙','旺','不'],

    '天府': ['庙','得','旺','得','旺','庙','得','旺','旺','得','庙','庙'],

    '太阴': ['陷','陷','陷','陷','陷','不','利','旺','旺','庙','庙','庙'],

    '天相': ['庙','平','得','得','庙','得','庙','平','得','得','庙','庙'],

    '天梁': ['庙','得','庙','陷','庙','旺','陷','得','得','陷','庙','旺'],

    '七杀': ['庙','旺','庙','平','旺','庙','庙','旺','庙','平','旺','庙'],

    '文曲': ['平','旺','庙','庙','陷','旺','得','庙','陷','旺','庙','庙'],

    '铃星': ['庙','利','得','得','庙','得','得','得','庙','陷','陷','陷'],

    '擎羊': ['','陷','庙','','陷','庙','','旺','庙','','旺','庙'],

    '武曲': ['得','利','庙','平','旺','庙','得','利','庙','平','旺','庙'],
    '廉贞': ['庙','平','利','陷','平','利','庙','平','利','陷','平','利'],
    '巨门': ['庙','庙','陷','旺','旺','不','庙','庙','陷','旺','旺','不'],
    '破军': ['得','陷','旺','平','庙','旺','得','陷','旺','平','庙','旺'],
};

astro.config({
  yearDivide: 'normal',
  brightness: DEFAULT_BRIGHTNESS,
});

const DEFAULT_LEAP_MONTH = 'split';
export type LunarMonthPolicy = 'split' | 'next-month' | 'prev-month' | 'origin-month';

export interface EffectiveLunarDate {
  lunarYear: number;
  lunarMonth: number;
  lunarDay: number;
  isLeapMonth: boolean;
  rawLunarMonth: number;
  rawLunarDay: number;
}

export function resolveEffectiveLunarDate(
  year: number,
  month: number,
  day: number,
  policy: LunarMonthPolicy = 'prev-month',
): EffectiveLunarDate {
  const lunar = Solar.fromYmd(year, month, day).getLunar();
  const rawLunarMonth = Number(lunar.getMonth());
  const rawLunarDay = Number(lunar.getDay());
  const isRawLeapMonth = rawLunarMonth < 0;
  const absoluteMonth = Math.abs(rawLunarMonth);

  if (!isRawLeapMonth) {
    return {
      lunarYear: Number(lunar.getYear()),
      lunarMonth: absoluteMonth,
      lunarDay: rawLunarDay,
      isLeapMonth: false,
      rawLunarMonth,
      rawLunarDay,
    };
  }

  let lunarYear = Number(lunar.getYear());
  let lunarMonth = absoluteMonth;
  let isLeapMonth = false;

  if (policy === 'split') {

    if (rawLunarDay > 15) lunarMonth = absoluteMonth + 1;
  } else if (policy === 'next-month') {
    lunarMonth = absoluteMonth + 1;
  } else if (policy === 'origin-month') {
    isLeapMonth = true;
  }

  if (lunarMonth > 12) {
    lunarMonth = 1;
    lunarYear += 1;
  }

  let lunarDay = rawLunarDay;
  // split is evaluated by iztro.bySolar on the original day; unlike byLunar
  // policies, its day must not be clamped to a different month's day count.
  if (policy !== 'split') try {
    const monthKey = isLeapMonth ? -lunarMonth : lunarMonth;
    const dayCount = LunarMonth.fromYm(lunarYear, monthKey)?.getDayCount?.();
    if (!Number.isInteger(dayCount) || dayCount! < 29 || dayCount! > 30)
      throw new Error('Cannot resolve target lunar month length');
    if (lunarDay > dayCount!) lunarDay = dayCount!;
  } catch (error) { throw new Error(`Lunar month policy failed: ${(error as Error).message}`); }

  return {
    lunarYear,
    lunarMonth,
    lunarDay,
    isLeapMonth,
    rawLunarMonth,
    rawLunarDay,
  };
}

export function getLunarInfo(
  year: number,
  month: number,
  day: number,
  hour?: number,
  policy: LunarMonthPolicy = 'prev-month',
): LunarInfo {
  const solar = Solar.fromYmd(year, month, day);
  const lunar = solar.getLunar();
  const effective = resolveEffectiveLunarDate(year, month, day, policy);

  const lu = lunar as any;

  const yearStem = STEMS.indexOf(lu.getYearGan());
  const yearBranch = BRANCHES.indexOf(lu.getYearZhi());

  return {
    lunarYear: effective.lunarYear,
    lunarMonth: effective.lunarMonth,
    lunarDay: effective.lunarDay,
    yearStem: yearStem >= 0 ? yearStem : 0,
    yearBranch: yearBranch >= 0 ? yearBranch : 0,
    isLeapMonth: effective.isLeapMonth,
    rawLunarYear: Number(lunar.getYear()),
    rawLunarMonth: effective.rawLunarMonth,
    rawLunarDay: effective.rawLunarDay,
    dayClamped: effective.lunarDay !== effective.rawLunarDay,
  };
}

const MING_ZHU_TABLE: Record<number, string> = {
  0: '贪狼', 1: '巨门', 2: '禄存', 3: '文曲', 4: '廉贞', 5: '武曲',
  6: '破军', 7: '武曲', 8: '廉贞', 9: '文曲', 10: '禄存', 11: '巨门',
};
const SHEN_ZHU_TABLE: Record<number, string> = {
  0: '火星', 6: '火星', 1: '天相', 7: '天相',
  2: '天梁', 8: '天梁', 3: '天同', 9: '天同',
  4: '文昌', 10: '文昌', 5: '天机', 11: '天机',
};
export function calcMingZhu(branch: number): string { return MING_ZHU_TABLE[branch] ?? ''; }
export function calcShenZhu(branch: number): string { return SHEN_ZHU_TABLE[branch] ?? ''; }
export function calcYinYangGender(yearStem: number, gender: 'male' | 'female'): string {
  return `${yearStem % 2 === 0 ? '阳' : '阴'}${gender === 'male' ? '男' : '女'}`;
}

function mapBrightness(b?: string): 'bright' | 'normal' | 'dim' {
  if (!b) return 'normal';
  if (b === '庙' || b === '旺') return 'bright';
  if (b === '陷' || b === '不' || b === '闲') return 'dim';
  return 'normal';
}

function extractRawBrightness(b?: string): import('./types').StarBrightness | undefined {
  if (!b) return undefined;
  const valid: import('./types').StarBrightness[] = ['庙', '旺', '得', '利', '平', '不', '闲', '陷', '地'];
  for (const x of valid) {
    if (b.includes(x)) return x;
  }
  return undefined;
}

const SHA_STARS = new Set(['擎羊', '陀罗', '火星', '铃星', '地空', '地劫',
  '天空', '旬空', '副旬', '截路', '截空', '副截', '大耗', '天使', '天伤',

  '天刑', '天哭', '天虚', '天月', '阴煞', '蜚廉', '空亡',
  '孤辰', '寡宿']);
const LUCKY_STARS = new Set(['文昌', '文曲', '左辅', '右弼', '天魁', '天钺',
  '禄存', '天马', '天官', '天福', '天才', '天寿', '三台', '八座', '恩光',
  '天贵', '台辅', '龙池', '凤阁', '红鸾', '天喜',

  '解神', '天德', '月德', '年解', '天巫', '华盖', '封诰']);

function mapStarType(starName: string, iztroType: string): Star['type'] {
  if (SHA_STARS.has(starName)) return 'sha';
  if (LUCKY_STARS.has(starName)) return 'lucky';
  const t = (iztroType ?? '').toLowerCase();
  if (t === '主星' || t === 'major') return 'major';
  if (t === '煞星' || t === 'tough') return 'sha';
  if (t === '吉星' || t === 'soft' || t === '禄存' || t === '天马') return 'lucky';
  return 'minor';
}

export function parseWuxingJu(name: string): number {
  const table: Record<string, number> = { '水二局': 2, '木三局': 3, '金四局': 4, '土五局': 5, '火六局': 6 };
  if (!(name in table)) throw new Error(`Unknown five-elements class: ${name}`);
  return table[name];
}

export function generateChart(
  birthInfo: BirthInfo,
  opts?: { leapMonth?: LunarMonthPolicy, sihuaProfile?: 'iztro' | 'quanshu' },
): ZiweiChart {
  const { year, month, day, hour, gender } = birthInfo;
  if (!Number.isInteger(hour) || hour < 0 || hour > 11) {
    throw new RangeError(`hour must be an integer branch index from 0 to 11; received ${hour}`);
  }

  const probe = new Date(Date.UTC(year, month - 1, day));
  if (
    !Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day) ||
    probe.getUTCFullYear() !== year || probe.getUTCMonth() !== month - 1 || probe.getUTCDate() !== day
  ) {
    throw new RangeError(`solar date does not exist: ${year}-${month}-${day}`);
  }
  const iztroGender = gender === 'male' ? '男' : '女';
  if (!['male', 'female'].includes(gender)) throw new Error('Invalid gender');
  const sihuaProfile = opts?.sihuaProfile ?? 'iztro';
  if (!['iztro', 'quanshu'].includes(sihuaProfile)) throw new Error('Unknown sihua profile');
  const mutagens: Record<string, string[]> = {};
  STEMS.forEach((stem, index) => { mutagens[stem] = [...SI_HUA_TABLE[index]]; });
  if (sihuaProfile === 'quanshu') mutagens['壬'] = ['天梁', '紫微', '天府', '武曲'];
  astro.config({ yearDivide: 'normal', brightness: DEFAULT_BRIGHTNESS, mutagens });

  const leapMode = opts?.leapMonth ?? DEFAULT_LEAP_MONTH;
  const effectiveLunar = resolveEffectiveLunarDate(year, month, day, leapMode);

  let astrolabe: any;

  if (leapMode !== 'split' && effectiveLunar.rawLunarMonth < 0) {

      const lunarDateStr = `${effectiveLunar.lunarYear}-${effectiveLunar.lunarMonth}-${effectiveLunar.lunarDay}`;
      astrolabe = astro.byLunar(
        lunarDateStr,
        hour,
        iztroGender,
        effectiveLunar.isLeapMonth,
        false,
        'zh-CN',
      );
  } else {

    astrolabe = astro.bySolar(`${year}-${month}-${day}`, hour, iztroGender, true, 'zh-CN');
  }

  const chartBirthInfo = {
    ...birthInfo,
    leapMonthPolicy: leapMode,
  } as BirthInfo & { leapMonthPolicy: LunarMonthPolicy };

  const palaces: Palace[] = astrolabe.palaces.map((p: any) => {
    const branch = BRANCHES.indexOf(p.earthlyBranch as string);
    const stem   = STEMS.indexOf(p.heavenlyStem as string);
    if (branch < 0 || stem < 0) throw new Error('Unrecognized palace stem/branch');

    const allStars: Star[] = [

      ...(p.majorStars ?? []).map((s: any) => {

        const rb = DEFAULT_BRIGHTNESS[s.name as string]?.[(branch + 10) % 12] ?? s.brightness;
        return {
          name:          s.name as string,
          type:          'major' as const,
          brightness:    rb ? mapBrightness(rb) : undefined,
          brightnessRaw: extractRawBrightness(rb),
          siHua:         s.mutagen as Star['siHua'],
        };
      }),

      ...(p.minorStars ?? []).map((s: any) => {

        const rb = DEFAULT_BRIGHTNESS[s.name as string]?.[(branch + 10) % 12] ?? s.brightness;
        return {
          name:          s.name as string,
          type:          mapStarType(s.name as string, s.type as string),
          brightness:    rb ? mapBrightness(rb) : undefined,
          brightnessRaw: extractRawBrightness(rb),
          siHua:         s.mutagen as Star['siHua'],
        };
      }),

      ...(p.adjectiveStars ?? []).map((s: any) => {

        const rb = DEFAULT_BRIGHTNESS[s.name as string]?.[(branch + 10) % 12] ?? s.brightness;
        return {
          name:          s.name as string,
          type:          mapStarType(s.name as string, (s.type as string) ?? ''),
          brightness:    rb ? mapBrightness(rb) : undefined,
          brightnessRaw: extractRawBrightness(rb),
          siHua:         s.mutagen as Star['siHua'],
        };
      }),
    ];

    for (const sname of [p.suiqian12, p.jiangqian12] as (string | undefined)[]) {
      if (sname === '劫煞' || sname === '龙德') {
        allStars.push({ name: sname, type: mapStarType(sname, '') });
      }
    }

    const range = p.decadal?.range;
    return {
      branch:        branch >= 0 ? branch : 0,
      stem:          stem >= 0 ? stem : 0,
      name:          p.name as string,
      stars:         allStars,
      daXianAge:     range ? [range[0], range[1]] as [number, number] : undefined,
      isMingGong:    p.name === '命宫',
      isShenGong:    p.isBodyPalace ?? false,
      isCurrentDaXian: false,
    };
  });

  const currentAge = 0;

  palaces.forEach(p => {
    if (p.daXianAge && currentAge >= p.daXianAge[0] && currentAge <= p.daXianAge[1]) {
      p.isCurrentDaXian = true;
    }
  });

  palaces.forEach(p => {
    p.oppositeBranch = (p.branch + 6) % 12;
    const mainStars = p.stars.filter(s => s.type === 'major');
    p.isEmpty = mainStars.length === 0;
    if (p.isEmpty) {
      const oppPalace = palaces.find(q => q.branch === p.oppositeBranch);
      if (oppPalace) {
        p.borrowedFromBranch = oppPalace.branch;
        p.borrowedFromName = oppPalace.name;
        p.borrowedStars = oppPalace.stars.filter(s => s.type === 'major').map(s => s.name);
      }
    }
  });

  const mingGongBranch = BRANCHES.indexOf(astrolabe.earthlyBranchOfSoulPalace as string);
  const shenGongBranch = BRANCHES.indexOf(astrolabe.earthlyBranchOfBodyPalace as string);
  if (mingGongBranch < 0 || shenGongBranch < 0) throw new Error('Unrecognized soul/body palace');
  const wuxingJuName   = astrolabe.fiveElementsClass as string;
  const wuxingJu       = parseWuxingJu(wuxingJuName);

  const ziweiPalace = palaces.find(p => p.stars.some(s => s.name === '紫微' && s.type === 'major'));
  if (!ziweiPalace) throw new Error('Ziwei star is missing');
  const ziweiPos    = ziweiPalace.branch;

  const daXians: DaXian[] = palaces
    .filter(p => p.daXianAge)
    .sort((a, b) => a.daXianAge![0] - b.daXianAge![0])
    .map(p => ({
      startAge:    p.daXianAge![0],
      endAge:      p.daXianAge![1],
      palaceBranch: p.branch,
      palaceName:   p.name,
    }));

  const currentDaXianIndex = daXians.findIndex(
    dx => currentAge >= dx.startAge && currentAge <= dx.endAge,
  );

  const lunarInfo = getLunarInfo(year, month, day, hour, leapMode);

  const mingZhu = calcMingZhu(mingGongBranch >= 0 ? mingGongBranch : 0);
  const shenZhu = calcShenZhu(lunarInfo.yearBranch);
  const yinYangGender = calcYinYangGender(lunarInfo.yearStem, gender);

  return {
    birthInfo: chartBirthInfo,
    lunarInfo,
    mingGongBranch: mingGongBranch >= 0 ? mingGongBranch : 0,
    shenGongBranch: shenGongBranch >= 0 ? shenGongBranch : 0,
    wuxingJu,
    wuxingJuName,
    ziweiPos,
    palaces,
    daXians,
    currentAge,
    currentDaXianIndex,
    mingZhu,
    shenZhu,
    yinYangGender,
  };
}
