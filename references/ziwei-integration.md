# 紫微模块接入（2.5）

用户要求紫微、双盘或八字与紫微比较时阅读本文件。保留原Python八字计算，紫微使用独立Node离线引擎。

## 使用

需要Python 3.9+与Node.js 18+；建议使用仍受维护的Node.js版本。发布包已含打包依赖，不需要npm install或API Key。仅算八字不需要Node。

```sh
python -X utf8 scripts/chart.py --birth "2014-11-13T15:16:00+08:00" --gender female --longitude 116.36 --clock apparent --ziwei --format markdown
python -X utf8 scripts/chart.py --lunar-date 2014-09-21 --lunar-leap --time 15:16 --utc-offset=+08:00 --gender female --ziwei
```

默认JSON；加--format markdown生成中文报告。可与--methods并用。Node不在PATH时用环境变量BAZI_NODE指定可执行文件绝对路径。

## 时间与流派

- 实际出生记录必须有历史UTC偏移。先归到UTC+8，再依--clock修正一次。不会再调用上游太阳时或夏令时修正程序。
- 八字年/月柱按实际瞬间交节；日/时按所选钟和--day-rule。紫微按所选钟的公历日与时辰索引，年按农历正月初一；不复用八字年柱作为紫微生年。
- --ziwei-day-rule next-day（默认）表示23点归次日；current-day表示23点仍归当日。它与八字--day-rule独立，必须在报告中标明。
- --ziwei-leap默认all，分别运行split、prev-month、next-month、origin-month。split前15日归原月，后半归下月；prev-month按原月份的普通月；next-month整月归下月；origin-month保留闰月、关闭分半。有效月份及日期截断行为继承上游，原始时间与实际农历另行保留。
- 用户有确定流派时可显式--ziwei-leap split等。不能根据往事吻合自动选流派或改出生时刻。
- --uncertainty仍是用户给出的±分钟，不把“前后”自动设为某个误差。太阳时额外±60秒是工程余量。紫微按秒扫描日期与时辰边界，并逐规则保留候选；上限沿用原入口0—120分钟。
- 大限仅给传统年龄区间，不按运行当天自动判断“当前大限”，也不直接折算成精确公历年。

## 输出与适配范围

JSON保留原八字字段，新增ziwei。variants按闰月策略列central与candidates，structure_stable_in_scanned_range反映该策略内时间候选是否改变结构。same_structure_across_selected_policies只比较各策略中央盘。一个候选输入可能对应多个相同盘，不据此投票。

每盘输出十二宫、主辅杂曜、本命四化、命身宫、五行局、命主身主、空宫借对宫和大限年龄区间。Markdown集中展示主星与四化；完整辅星和各候选见JSON。

来源：<https://github.com/Renhuai123/ziwei-doushu>，下载日期2026-10-17。选取排盘流程、类型、常量；实际来源文件与本地文件哈希在scripts/ziwei/provenance.json，代码许可在LICENSE.upstream，运行依赖许可在THIRD_PARTY_NOTICES.txt。

本地profile为classic-table-adapter-v1：保留上游经典DEFAULT_BRIGHTNESS，排除明确取自文墨表的贪狼条目，缺项回退iztro。没有复制wenmo-data、wenmo-tables.generated及相关补丁。此口径与上游当前文墨模式不同，不声称复刻其整盘，也不把上游网页宣传当作核验结论。

上游时辰中点计算的fourPillars/fourPillarsLunar已从紫微输出删除；八字只采用Python精确出生时刻结果。移除依赖运行日期的年龄和当前大限字段，保证本命结果可复现。

没有引入海量解读集、商业断语库、倪师逐字稿或AI后端。现有作者登记模块不把紫微结构自动归为“倪海厦已核对规则”。要新增传统解释，逐条登记条件、书名、章节和可核对来源，再接入；不根据宫名诊断健康或给儿童固定能力标签。

## 维护与核验

运行python -m unittest discover -s scripts -p "test_*.py"。Node缺失时紫微引擎测试会明确跳过，不能据此宣称完整双盘核验通过；CI已加入Node步骤。

新增验证涵盖96张跨年代盘的十二宫、十四主星、四化和独立命身宫公式，以及闰月、晚子时、历史偏移、时辰边界、离线CLI。结构测试不是紫微预测效度证明，也不是逐星对所有流派的全面校勘。

重建仅供维护者：进入scripts/ziwei，安装pnpm后运行pnpm install --frozen-lockfile --ignore-scripts，再node build.cjs。检查生成bundle哈希、依赖许可证和provenance，运行测试后一起提交源码与engine.cjs。用户运行不需要这些构建工具。
