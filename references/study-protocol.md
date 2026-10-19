# 过去盲测与未来登记

study.py是本地研究记录工具，不是预测引擎。示例只有虚构A/B，不能用于宣传准确率。

先写plan.json：mode（retrospective/prospective）、split（development/holdout）、匿名subjects、完整years、categories、definitions事件定义/排除项/证据标准、rules_version、engine_version、threshold、prediction_cutoff（含偏移）。实例见assets/examples/study-plan.json。

类别限education_change、residence_change、job_change、relationship_change，必须具体定义，不能把一切好坏都叫“变化”。每人每年每类都交完整观察格，不能只提交说中的几项。

## 历史盲测
```sh
python scripts/study.py init --root experiments/demo --file assets/examples/study-plan.json
python scripts/study.py commit-truth --root experiments/demo --file assets/examples/study-truth.json
python scripts/study.py public-input --root experiments/demo
python scripts/study.py register --root experiments/demo --file assets/examples/study-predictions.json
python scripts/study.py evaluate --root experiments/demo
```

经历由另一位保管人管理。标签保存在private/truth.json，公开入口不读取它；承诺文件保存带随机盐的哈希。预测者只看允许的出生资料，不打开private、不追问经历；已经知道经历就不能称盲测。

必须提交model和age_background_baseline，另可加shuffled_chart_baseline，均在揭晓前生成。基准不能在知道答案后故意编差。probability是登记者的判断，不是本项目证明的概率。

outcome为1（符合预定义事件）、0（证据支持没有）、null（不可核实）；null单列不算命中或错误。注册文件不覆盖，改规则另建development研究；不能在同一批案例上改完规则又称独立holdout。

## 未来登记
mode改prospective，截止晚于创建时刻，目标年份不早于截止年份。先register，事件发生后commit-truth。未来不能已有结果，当年未结束不能判“全年没有发生”。一项研究只提交一份结果，未到期填null；要逐年复盘可预先拆分研究，不覆盖旧记录。

时间戳来自本机时钟，哈希用于发现意外修改。能改文件和时钟的人能伪造，因此不构成第三方不可篡改证明。正式研究需要独立保管人、外部时间戳与评价者。

## 结果
输出TP/FP/FN/TN、可核实数量、精确率、召回率、Brier误差及与年龄背景基准的差。Brier越低越好，这批结果更好不等于普遍有效。

Wilson区间只是描述；同一个人的年份有关联，不能当作按人聚类的正式统计检验。需要更多独立样本、外部评价及真正前瞻测试。不要强迫用户披露经历；experiments已被.gitignore排除，private目录不要公开上传。
