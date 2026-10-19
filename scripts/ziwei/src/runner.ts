import { readFileSync } from 'node:fs';
import { generateChart, parseWuxingJu } from './upstream/algorithm';
import type { BirthInfo } from './upstream/types';

const policies = new Set(['split', 'prev-month', 'next-month', 'origin-month']);
try {
  if (process.argv.includes('--self-test')) {
    if (parseWuxingJu('火六局') !== 6) throw new Error('Known class failed');
    let rejected = false;
    try { parseWuxingJu('未知局'); } catch { rejected = true; }
    if (!rejected) throw new Error('Unknown class was silently accepted');
    process.stdout.write(JSON.stringify({ unknownClassRejected: true }));
    process.exit(0);
  }
  const payload = JSON.parse(readFileSync(0, 'utf8'));
  if (!Array.isArray(payload.requests) || payload.requests.length < 1 || payload.requests.length > 64)
    throw new Error('requests must contain 1..64 charts');
  const result = payload.requests.map((request: any) => {
    const b = request.birthInfo as BirthInfo;
    if (!b || !['male', 'female'].includes(b.gender) || !policies.has(request.leapMonth))
      throw new Error('Explicit gender and leap-month policy required');
    if (!Number.isInteger(b.year) || b.year < 1950 || b.year > 2050)
      throw new Error('Supported chart years: 1950..2050');
    const sihuaProfile = request.sihuaProfile ?? 'iztro';
    if (!['iztro', 'quanshu'].includes(sihuaProfile)) throw new Error('Unknown sihua profile');
    const chart = generateChart(b, { leapMonth: request.leapMonth, sihuaProfile });
    const majors = chart.palaces.flatMap(p => p.stars.filter(s => s.type === 'major').map(s => s.name));
    if (chart.palaces.length !== 12 || new Set(chart.palaces.map(p => p.branch)).size !== 12 ||
        majors.length !== 14 || new Set(majors).size !== 14)
      throw new Error('Incomplete chart: missing or duplicate palaces/major stars');
    // Upstream uses a branch midpoint for these fields; never present them as
    // the exact-time bazi, nor make natal output depend on the execution date.
    const { fourPillars, fourPillarsLunar, ...lunar } = chart.lunarInfo;
    const { currentAge, currentDaXianIndex, ...natal } = chart;
    return {
      ...natal, lunarInfo: lunar,
      palaces: chart.palaces.map(({ isCurrentDaXian, ...p }) => p)
        .sort((a, b) => a.branch - b.branch),
    };
  });
  process.stdout.write(JSON.stringify(result));
} catch (error) {
  process.stderr.write(`Ziwei calculation failed: ${(error as Error).message}\n`);
  process.exitCode = 1;
}
