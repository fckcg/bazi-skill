# bazi 修复版 2.5.1

本包是 fckcg/bazi-skill 的本地修订版，未发布到上游仓库。

## 紫微与双盘（新增）

保留原八字与名家模块，新增Renhuai123/ziwei-doushu排盘流程的独立适配。紫微运行需要Node.js 18+；约1.3MB的离线引擎已包含依赖，不需要npm install、API Key或上传出生资料。仅算八字仍只需要Python。

```sh
python -X utf8 scripts/chart.py --birth "2014-11-13T15:16:00+08:00" --gender female --longitude 116.36 --clock apparent --ziwei --format markdown
```

默认比较四种闰月策略，支持十二宫、星曜、本命四化、大限年龄、时间边界候选及JSON/Markdown报告。--ziwei-leap可选定规则；--ziwei-day-rule单独指定紫微晚子时口径。详见references/ziwei-integration.md。

这是本地经典表适配，未引入文墨反编译表、商业断语库、海量数据集或AI接口，不等同上游网站全部功能。来源和修改记录在scripts/ziwei/provenance.json，保留MIT和各运行依赖许可。

## 使用
Python 3.9+，依赖已随附，无须联网安装。
在本目录执行：
```
python scripts/chart.py --birth "2014-11-13T15:16:00+08:00" --gender female --longitude 117.03 --clock apparent --uncertainty 5
python -m unittest discover -s scripts -p "test_*.py"
```
示例误差仅演示参数，不是对实际用户时间误差的认定。
其他选项请运行 --help。默认standard标准时，支持mean/apparent和三种换日规则。
JSON记录计算版本、时间约定、修正、四柱、大运、候选盘及误差端点。

## 修复
- 停用未经核对的手工节气表，接入固定版本lunar_python 1.4.8。
- 将实际瞬间和太阳钟分开，避免错误移动年/月交节边界。
- 明确平太阳时与真太阳时差异；均时差仍为近似，边界需复核。
- 出生时间不确定时扫描候选盘，不以往事拟合确定时辰。
- 重写技能入口，去除强制断事、器官疾病预测和无依据准确率。
- 旧参考材料移除数值百分比，并标明未经实证验证，仅用于传统文化解释。
- 当前78项回归测试（含2424项日期和432项时刻比对、96张紫微结构样例、37个闰月的296组月中规则组合），含输入校验、历表抽查、换日、历史时区偏移和时辰/节气边界。

## 限制
支持1950—2050出生年份；时区偏移由调用者核实，暂未自动接入历史时区库。
节气日期核验覆盖1950—2050，时刻核验覆盖2010—2027；1979大寒保留一个已知日期差异。详见references/calendar-validation.md。
传统规则未建立预测效度，不能据此诊断疾病、限定孩子能力或决定投资。
均时差额外±60秒为工程余量，不是严格误差上界。
原始项目和随附依赖的许可证分别保留于LICENSE和scripts/vendor的dist-info/licenses。

## 农历输入
农历日期格式为年-月-日。普通月不加闰月参数，闰月必须加 --lunar-leap：
```
python scripts/chart.py --lunar-date 2014-09-21 --lunar-leap --time 15:16 --utc-offset=+08:00 --gender female
```
转换结果为公历2014-11-13。JSON保留原始日期、闰月标记和转换后的公历时刻。
直接农历入口采用中国农历日期，支持UTC+8和核实后的中国历史夏令时UTC+9；海外农历日期先明确当地历法及日期约定，再换成公历并使用 --birth。
程序校验闰月是否存在、月份天数、时间及参数冲突；不会把非法日期自动挪到下月。

## 自动测试
仓库新增 .github/workflows/tests.yml，在push、pull_request或手动触发时，在Windows/Ubuntu及Python 3.9/3.13组合上运行离线测试与农历入口检查。
运行时不需要下载历法依赖或官方历表。工作流使用只读仓库权限。
此配置需要上传到GitHub才会执行；本地通过不等于远端四种组合已经通过。

## 参考资料修订
重写健康象义、五运六气、传统断事、紫微比较四个文件；其余相关材料中的保证式表述已改为未验证的传统象义。经典引文保留并标明出处性质。修改记录见references/editorial-cleanup.json。
原始版本及上一版完整备份保存在交付目录，本包保留历史文化研究用途，但不包含个人健康预测表。

## 名家模块与对比
```
python scripts/methods.py --list
python scripts/chart.py --birth "2014-11-13T15:16:00+08:00" --gender female --methods shen-xiaozhan,ren-tieqiao,yu-chuntai
python scripts/chart.py --birth "2014-11-13T15:16:00+08:00" --methods all
```
15位作者各有独立档案、来源和核对清单；当前10条文本规则可执行结构检查，其余仅提供待核对的研究路径。结果不模拟作者人格或承诺事件预测。
资料入口：references/master-methods.md；结构化登记：references/method-registry.json。
纠正袁树珊著作的明代归属，统一穷通宝鉴书名，分开沈氏原文与徐注。保留时间不确定性与各派分歧，不将结果投票合并成吉凶。

## 中文报告与候选比较（2.4）
```
python -X utf8 scripts/chart.py --birth "2014-11-13T15:16:00+08:00" --longitude 117.03 --clock apparent --uncertainty 20 | python -X utf8 scripts/methods.py --chart-json - --select chen-suan,wei-qianli,yuan-shushan --format markdown
```
管道输入不要求先写出生信息文件。报告显示各候选四柱、每条规则的检查结果、是否随候选变化、来源范围及未核实归属。
当前8个模块的所列原文段落已核对，共10条有限结构规则。其余作者仍待正文核对，不宣称全部理论已实现。
原文核对范围见references/source-review-scopes.md。程序会拒绝没有对应来源、未核对、错属作者或登记不一致的规则。
