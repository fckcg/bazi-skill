# 节气计算与核对

旧1950—2050手工节气表已停用，不可作为排盘输入。
已确认旧表2014立冬为11-08 00:57，香港天文台为11-07 20:07。
新计算采用固定版本 lunar_python 1.4.8 的天文历法算法；秒级显示不代表秒级官方认证。
用 scripts/chart.py 获取出生时刻前后的节及起运目标节。月份只以十二“节”切换。
立春同时用于年柱切换。所有交节比较基于同一个实际瞬间，使用UTC+8。
不得用经度修正后的墙上时间直接与UTC+8节气表比较。
核对源：https://www.hko.gov.hk/tc/gts/astron2014/files/2014cal11.pdf
https://www.hko.gov.hk/tc/gts/astron2014/files/2014cal12.pdf
https://eco.mtk.nao.ac.jp/koyomi/yoko/2014/rekiyou142.html
核验范围见 calendar-validation.md；未证明1950—2050所有节气时刻误差上界。
