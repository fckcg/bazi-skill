# 名家模块与来源状态

来源分级：text_excerpt_checked只表示所列段落已核对；bibliography_checked表示书目/目录已核对；bibliography_provisional表示仍需更可靠的书目。任何状态都不等于预测有效，也不表示已掌握整本著作。

规则注册在method-registry.json，只有登记为已核对且有章节定位的规则可以归属作者。其余流程是项目设计的研究清单。

| 作者 | 关注点 | 核对状态 | 独立说明 |
|---|---|---|---|
| 沈孝瞻 | 格局法 | text_excerpt_checked | [模块](methods/shen-xiaozhan.md) |
| 任铁樵 | 气势与根气 | text_excerpt_checked | [模块](methods/ren-tieqiao.md) |
| 徐乐吾 | 评注比较 | text_excerpt_checked | [模块](methods/xu-lewu.md) |
| 余春台 | 调候法 | text_excerpt_checked | [模块](methods/yu-chuntai.md) |
| 万民英 | 经典汇编 | bibliography_checked | [模块](methods/wan-minying.md) |
| 张楠 | 病药法 | text_excerpt_checked | [模块](methods/zhang-nan.md) |
| 韦千里 | 讲义与案例 | bibliography_checked | [模块](methods/wei-qianli.md) |
| 梁湘润 | 子平母法研究 | bibliography_checked | [模块](methods/liang-xiangrun.md) |
| 陈素庵 | 条件与用神讨论 | bibliography_checked | [模块](methods/chen-suan.md) |
| 袁树珊 | 文献与术语 | bibliography_checked | [模块](methods/yuan-shushan.md) |
| 邹文耀 | 分歧与考证 | bibliography_checked | [模块](methods/zou-wenyao.md) |
| 段建业 | 盲派理象研究 | bibliography_checked | [模块](methods/duan-jianye.md) |
| 吴俊民 | 近现代理论研究 | bibliography_checked | [模块](methods/wu-junmin.md) |
| 何建忠 | 心理象义研究 | bibliography_checked | [模块](methods/he-jianzhong.md) |
| 钟义明 | 近现代案例研究 | bibliography_provisional | [模块](methods/zhong-yiming.md) |

## 执行
运行 scripts/methods.py --list；或在排盘时加 --methods all 或 --methods shen-xiaozhan,ren-tieqiao。
每个模块返回来源、适用范围、结构证据、已核对规则和待核对内容。避免模仿大师语气，不将通用口诀归属某位作者。
待核对状态须明确告知用户，不能填补虚构规则。旧文中的人物生卒年、医疗预测及量化方法归属已退出使用，原文在版本备份中。
