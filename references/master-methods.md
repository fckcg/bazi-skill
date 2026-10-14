# 名家模块与来源状态

所列段落已核对不等于整本书已校勘，也不等于预测有效。书目状态不能用于证明具体规则。
当前15位作者档案，8个模块共10条原文段落的结构核对规则。原文、网站译文与项目推演分别处理。
数字转录中可能有错别字、篇章号及版本差异；本版不虚构印本页码，不继承未核对的断语。

| 作者 | 关注点 | 状态 | 独立说明 |
|---|---|---|---|
| 沈孝瞻 | 格局法 | text_excerpt_checked | [模块](methods/shen-xiaozhan.md) |
| 任铁樵 | 气势与根气 | text_excerpt_checked | [模块](methods/ren-tieqiao.md) |
| 徐乐吾 | 评注比较 | text_excerpt_checked | [模块](methods/xu-lewu.md) |
| 余春台 | 调候法 | text_excerpt_checked | [模块](methods/yu-chuntai.md) |
| 万民英 | 经典汇编 | bibliography_checked | [模块](methods/wan-minying.md) |
| 张楠 | 病药法 | text_excerpt_checked | [模块](methods/zhang-nan.md) |
| 韦千里 | 讲义与案例 | text_excerpt_checked | [模块](methods/wei-qianli.md) |
| 梁湘润 | 子平母法研究 | bibliography_checked | [模块](methods/liang-xiangrun.md) |
| 陈素庵 | 条件与用神讨论 | text_excerpt_checked | [模块](methods/chen-suan.md) |
| 袁树珊 | 文献与术语 | text_excerpt_checked | [模块](methods/yuan-shushan.md) |
| 邹文耀 | 分歧与考证 | bibliography_checked | [模块](methods/zou-wenyao.md) |
| 段建业 | 盲派理象研究 | bibliography_checked | [模块](methods/duan-jianye.md) |
| 吴俊民 | 近现代理论研究 | bibliography_checked | [模块](methods/wu-junmin.md) |
| 何建忠 | 心理象义研究 | bibliography_checked | [模块](methods/he-jianzhong.md) |
| 钟义明 | 近现代案例研究 | bibliography_provisional | [模块](methods/zhong-yiming.md) |

## 执行与比较
chart.py可加 --methods all 或作者id。methods.py --list 查看档案。
methods.py --chart-json - --format markdown 支持读取管道JSON输出中文可读报告。
多候选盘逐条执行规则，并标明规则检查是否稳定；不得只取中央盘的结论。
陈素庵与任铁樵关于藏干分日的相关段落保留解释分歧，属于方法约定差异，不用多数投票裁决。
来源未核对、错属作者、缺定位或登记不一致时，程序拒绝启用该规则。
