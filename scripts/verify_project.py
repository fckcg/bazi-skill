"""Run the actual suite and generate version/coverage documentation from its result."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parent.parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',required=True)
    parser.add_argument('--update-docs',action='store_true')
    args=parser.parse_args()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'scripts'),pattern='test_*.py')
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    from chart import VERSION
    from birth_record import tzdata
    from methods import load_registry
    from ziwei_bridge import ROOT as ZROOT
    fixtures=json.loads((ROOT/'references/calendar-fixtures.json').read_text(encoding='utf-8'))
    extra=json.loads((ROOT/'references/calendar-extra-fixtures.json').read_text(encoding='utf-8'))
    solar=json.loads((ROOT/'references/solar-fixtures.json').read_text(encoding='utf-8'))
    package=json.loads((ZROOT/'provenance.json').read_text(encoding='utf-8'))
    times=fixtures['naoj_times']+extra['naoj_times']
    status={'version':VERSION,'generated_utc':datetime.now(timezone.utc).isoformat(),
            'python':platform.python_version(),'tests_run':result.testsRun,'skipped':len(result.skipped),
            'failures':[t.id() for t,_ in result.failures],'errors':[t.id() for t,_ in result.errors],
            'passed':result.wasSuccessful(),'hko_date_checks':len(fixtures['hko_dates']),
            'naoj_time_checks':len(times),'naoj_time_years':sorted({r['year'] for r in times}),
            'noaa_model_implementation_samples':len(solar['rows']),
            'tzdata':tzdata.__version__,'iana':tzdata.IANA_VERSION,
            'author_profiles':len(load_registry()['profiles']),'active_text_rules':len(load_registry()['rules']),
            'ziwei_bundle_sha256':package['bundle_sha256'],
            'limitations':['1979 Dahan date discrepancy retained.',
                          'Solar model cross-language agreement is not independent ephemeris certification.',
                          'Independent ziwei reference checks listed structural formulas, not all brightness/minor stars.',
                          'No empirical prediction validity has been established.']}
    report=Path(args.report);report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.update_docs and result.wasSuccessful() and not result.skipped:
        text=(f"# 自动生成的验证状态\n\n版本：{VERSION}。Python：{status['python']}。\n\n"
              f"- 实际执行{result.testsRun}项测试，失败0、错误0、跳过0。\n"
              f"- 香港天文台节气日期：{status['hko_date_checks']}项，保留1979大寒的已知午夜日期差异。\n"
              f"- 日本国立天文台分钟时刻：{len(times)}项，覆盖{min(status['naoj_time_years'])}—{max(status['naoj_time_years'])}，已观察最大差31秒。\n"
              f"- NOAA模型跨语言实现对照：{len(solar['rows'])}项；不是独立星历误差认证。\n"
              f"- 离线时区：tzdata {tzdata.__version__}，IANA {tzdata.IANA_VERSION}。\n"
              f"- 名家档案{status['author_profiles']}位，启用的有限文本规则{status['active_text_rules']}条。\n\n"
              "独立紫微核对包括240组跨年/时辰/性别盘，并保留37个闰月296组策略测试。只核对所列结构，不证明性格或现实事件预测准确。\n\n"
              "此页由scripts/verify_project.py --update-docs生成。CI运行时另外输出实际报告，不能把本地通过等同远端通过。\n")
        (ROOT/'references/verification-summary.md').write_text(text,encoding='utf-8')
        (ROOT/'references/verification-status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'version':VERSION,'tests':result.testsRun,'passed':result.wasSuccessful(),'skipped':len(result.skipped)},ensure_ascii=False))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__': sys.exit(main())
