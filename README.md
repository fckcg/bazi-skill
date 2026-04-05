![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-blueviolet)
![AgentSkills](https://img.shields.io/badge/AgentSkills-Standard-green)

# 赛博算命 Skill

基于 Claude Code 的八字排盘与命理分析工具。通过交互式对话收集出生信息，排出四柱八字，支持五大流派及混合模式分析。

## 功能

- **流派选择** — 支持五大流派（经典派、徐五行、李涵琛、香港-台湾、心理学派）及混合模式
- **信息收集** — 逐步收集姓名、阳历/农历生日、出生时辰、性别、出生地等信息
- **排盘计算** — 自动排出年柱、月柱、日柱、时柱，计算大运与流年
- **差异化分析** — 根据选定流派，提供不同侧重点的综合分析和建议
- **流派对标验证** — 通过历史事件验证分析准确度，自动微调分析模型

## 支持的分析流派

| 流派 | 核心侧重 | 适用场景 |
|------|---------|---------|
| **经典派**（传统九本典籍）| 格局、用神、大运 | 传统深度分析 |
| **徐五行学派** | 五行平衡、调理建议 | 身心调理、日常优化 |
| **李涵琛学派** | 心理格局、性格特质 | 自我认知、成长导向 |
| **香港-台湾学派** | 实用预测、近期运势 | 关键决策、具体预测 |
| **心理学基础学派** | 心理健康、心理调适 | 心理成长、情绪管理 |
| **混合分析** | 多流派综合 | 全面综合分析 |

## 安装

> **注意**：Claude Code 从 git 仓库根目录的 `.claude/skills/` 查找 skill，请在正确的位置执行。

```bash
# 安装到当前项目（在 git 仓库根目录执行）
mkdir -p .claude/skills
git clone https://github.com/jinchenma94/bazi-skill .claude/skills/bazi

# 或安装到全局（所有项目都能用）
git clone https://github.com/jinchenma94/bazi-skill ~/.claude/skills/bazi
```

## 使用

在 Claude Code 中输入以下任意关键词即可触发：

`算八字` `看八字` `批八字` `排八字` `四柱` `命盘` `算命` `排盘` `bazi`

触发后，Skill 会首先询问您希望使用哪种流派（Step 0），然后逐步引导您提供出生信息，最后根据所选流派进行排盘和差异化综合分析。

## 参考典籍（经典派）

| 典籍 | 简称 |
|------|------|
| 《穷通宝典》 | 论日主调候 |
| 《三命通会》 | 论格局神煞 |
| 《滴天髓》 | 论五行旺衰 |
| 《渊海子平》 | 论十神六亲 |
| 《千里命稿》 | 论命例实证 |
| 《协纪辨方书》 | 论择日神煞 |
| 《果老星宗》 | 论星命合参 |
| 《子平真诠》 | 论用神格局 |
| 《神峰通考》 | 论命理辨误 |

## 项目结构

```
bazi-skill/
├── SKILL.md                              # Skill 入口（含流派选择逻辑）
├── references/                           # 参考文件
│   ├── wuxing-tables.md                  #   五行、天干地支、十神参考表
│   ├── shichen-table.md                  #   时辰对照表、日上起时法
│   ├── dayun-rules.md                    #   大运顺逆排规则、起运年龄计算
│   ├── classical-texts.md                #   九本经典典籍核心规则摘要
│   ├── shensha-guide.md                  #   神煞吉凶详解
│   ├── shishen-analysis.md               #   十神分析详解
│   ├── shishen-combinations.md           #   十神组合分析
│   ├── schools-framework.md              #   五大流派框架总览与对比
│   ├── schools-comparison.md             #   各流派论命差异对比表
│   ├── shensha-by-schools.md             #   神煞在各流派中的应用差异
│   ├── xu-wuxing-school.md               #   徐五行学派专属工具
│   ├── li-hanchen-school.md              #   李涵琛学派专属工具
│   ├── hong-kong-taiwan-school.md        #   香港-台湾学派专属工具
│   └── psychology-school.md             #   心理学基础学派专属工具
├── LICENSE
└── README.md
```

## 免责声明

本 Skill 仅供传统文化学习与娱乐参考，分析结果不构成任何决策依据。命理学属于传统文化范畴，请理性看待。
