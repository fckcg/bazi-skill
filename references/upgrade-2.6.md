# 2.6使用与维护

## 本地表单
运行python -X utf8 scripts/local_app.py，在浏览器打开http://127.0.0.1:8765，Ctrl+C退出。表单提供出生资料、十二宫图、规则/时间候选切换和报告下载。仅监听本机，不自动保存资料，无外部脚本、地图、账号或支付。表单使用公历；农历仍可使用chart.py原有参数。主动下载的记录含出生资料，分享前自行检查。

## 出生资料
--record assets/examples/birth-record.json读取结构化记录；--record -从标准输入读取。命令行与记录字段冲突时报错。

- uncertainty_minutes为null或省略：误差未知，不能确认真实全范围稳定。
- 0：调用者明确按记录时刻计算，不代表第三方认证。
- 1—120：用户提供的±分钟；更大范围分段覆盖，不截断。
- time_source为birth_certificate、hospital_record、family_memory或unknown。来源与误差分开；出生证明也可有未知误差。
- place和longitude_source记录地点与坐标依据；县城坐标不能当医院坐标，本版不自动地理编码。

旧字段pillars_stable_in_scanned_range保留兼容，只代表名义扫描；新字段stability_confirmed_for_reported_range在误差未知时为null。紫微同样标明uncertainty_known，不以名义扫描宣称实际稳定。

## 时区、太阳时与起运
--timezone Asia/Shanghai解析当地时间或核对给定偏移，采用随包固定的tzdata 2026.5 / IANA 2026e。跳钟导致的不存在时间拒绝；回拨重复时间须指定--fold 0/1或明确偏移。偏移冲突不默默覆盖。历史有争议时仍核实原始记录，数据库不认证出生证明。来源：<https://www.iana.org/time-zones>，许可证在scripts/vendor/tzdata-2026.5.dist-info/licenses。

均时差改用NOAA/Meeus儒略世纪模型。120组来自NOAA官方JavaScript的对照验证跨语言实现；这是同模型对照，不是独立星历或秒级误差认证，额外±60秒仍仅是工程余量。NOAA已说明网页工具不再积极维护，不能据此担保精度。来源：<https://gml.noaa.gov/grad/solcalc/calcdetails.html>。

qiyun_segments在给定误差跨节或UTC+8午夜时分段，列左右探针、目标节及右端是否包含。分钟起运有取整，探针不是严格极值；误差未知不生成伪造区间。

## 紫微独立核对
独立Python实现核对命身、五行局、14主星与10辅曜、四化和大限，代码在ziwei_reference.py。参考《紫微斗数全书》卷二的安星公式；起紫微用局数/日数除法奇偶的项目实现，不冒充古籍逐字算法。每个候选带independent_check和differences，差异不投票消除。未覆盖所有杂曜与亮度，也不能保证两实现无共同历法或解释偏差。

--sihua-profile iztro为现代引擎表；quanshu按所核对四化诀取壬年天府化科，与默认左辅化科明确区分。每次重设完整表，避免批量切换污染；不代表作者全套流派，闰月/晚子时另行配置。固定来源：<https://zh.wikisource.org/w/index.php?oldid=1963110&title=紫微斗數全書/卷二>。正文人生断语未作为实际事件预测引入。

## 验证与规则
15位作者与10条有限文本规则保留，不冒充完整理论。作者规则输出registry_sha256，历法输出计算源码哈希，紫微保留构建哈希。

新增2004—2009官方分钟时刻144项，合计2004—2027的576项。所尝试2000—2003年鉴地址返回404，记录在calendar-extra-fixtures.json，不代表其他渠道没有资料。其他年份完整分钟核验尚未完成。

运行python scripts/verify_project.py --report verification-run.json --update-docs，只有全通过且无跳过才更新verification-summary.md。统计从实际运行生成，避免旧数字残留；本地通过不等于GitHub远端通过。

盲测与未来登记见study-protocol.md。工具帮助记录和评估，不生成预测或证明断事能力。
