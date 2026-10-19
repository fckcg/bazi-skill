"""Independent Python structural reference, not a copy of the JS engine.

Conventions: Quanshu vol.2 textual formulas; ziwei seed uses division/parity.
Only the listed stars are checked. Modern iztro Ren-year sihua is a named variant.
"""
from chart import lunar_at
from datetime import datetime

SOURCE = 'https://zh.wikisource.org/wiki/紫微斗數全書/卷二'
GAN = '甲乙丙丁戊己庚辛壬癸'
NAYIN = '金火木土金火水土金木水土火木水金火木土金火水土金木水土火木水'
SLOTS = {'水': 2, '木': 3, '金': 4, '土': 5, '火': 6}
SIHUA = [
    ['廉贞','破军','武曲','太阳'], ['天机','天梁','紫微','太阴'],
    ['天同','天机','文昌','廉贞'], ['太阴','天同','天机','巨门'],
    ['贪狼','太阴','右弼','天机'], ['武曲','贪狼','天梁','文曲'],
    ['太阳','武曲','太阴','天同'], ['巨门','太阳','文曲','文昌'],
    ['天梁','紫微','天府','武曲'], ['破军','巨门','太阴','贪狼']]


def reference(birth, policy='split', sihua_profile='iztro'):
    lunar = lunar_at(datetime(birth['year'], birth['month'], birth['day']))
    year, raw_month, day = lunar.getYear(), lunar.getMonth(), lunar.getDay()
    month = abs(raw_month)
    if raw_month < 0 and (policy == 'next-month' or policy == 'split' and day > 15):
        month += 1
    if month > 12:
        year, month = year+1, 1
    if raw_month < 0 and policy not in ('split', 'origin-month'):
        from lunar_python import LunarMonth
        day = min(day, LunarMonth.fromYm(year, month).getDayCount())
    stem, ybranch = (year-4) % 10, (year-4) % 12
    h = birth['hour']
    ming, shen = (month+1-h) % 12, (month+1+h) % 12
    palace_stem = ((stem % 5)*2+2+(ming-2) % 12) % 10
    gz_index = next(i for i in range(60) if i % 10 == palace_stem and i % 12 == ming)
    bureau = SLOTS[NAYIN[gz_index//2]]
    quotient, rem = divmod(day, bureau)
    pad = (bureau-rem) % bureau
    step = quotient + bool(rem)
    zw = (1+step + (-pad if pad % 2 else pad)) % 12
    tf = (4-zw) % 12
    stars = {n: (zw+offset) % 12 for n, offset in [('紫微',0),('天机',-1),('太阳',-3),
             ('武曲',-4),('天同',-5),('廉贞',-8)]}
    stars.update({n: (tf+offset) % 12 for n, offset in [('天府',0),('太阴',1),('贪狼',2),
                 ('巨门',3),('天相',4),('天梁',5),('七杀',6),('破军',10)]})
    stars.update({'文昌':(10-h)%12, '文曲':(4+h)%12, '左辅':(month+3)%12,
                  '右弼':(11-month)%12, '红鸾':(3-ybranch)%12, '天喜':(9-ybranch)%12,
                  '禄存':[2,3,5,6,5,6,8,9,11,0][stem]})
    stars.update({'擎羊':(stars['禄存']+1)%12, '陀罗':(stars['禄存']-1)%12,
                  '天马':{0:2,1:11,2:8,3:5}[ybranch%4]})
    row = SIHUA[stem][:]
    if sihua_profile == 'iztro' and stem == 8:
        row[2] = '左辅'
    direction = 1 if (stem % 2 == 0) == (birth['gender'] == 'male') else -1
    return {'ming':ming, 'shen':shen, 'bureau':bureau, 'stars':stars,
            'sihua': dict(zip(['禄','权','科','忌'],row)),
            'decades':[{'branch':(ming+direction*i)%12, 'age':[bureau+10*i,bureau+10*i+9]} for i in range(12)]}


def audit(chart, policy, sihua_profile='iztro'):
    expected = reference(chart['birthInfo'], policy, sihua_profile)
    issues = []
    for name, actual in [('ming',chart['mingGongBranch']),('shen',chart['shenGongBranch']),('bureau',chart['wuxingJu'])]:
        if actual != expected[name]: issues.append({'field':name,'expected':expected[name],'actual':actual})
    positions = {s['name']:p['branch'] for p in chart['palaces'] for s in p['stars']}
    for name, branch in expected['stars'].items():
        if positions.get(name) != branch:
            issues.append({'field':name,'expected':branch,'actual':positions.get(name)})
    sihua = {s['siHua']:s['name'] for p in chart['palaces'] for s in p['stars'] if s.get('siHua')}
    if sihua != expected['sihua']: issues.append({'field':'sihua','expected':expected['sihua'],'actual':sihua})
    decades = [{'branch':d['palaceBranch'],'age':[d['startAge'],d['endAge']]} for d in chart['daXians']]
    if decades != expected['decades']: issues.append({'field':'decades','expected':expected['decades'],'actual':decades})
    return {'source':SOURCE, 'implementation':'independent-python-formulas-v1',
            'scope':'命身宫、五行局、14主星与10辅曜、四化、大限；不含亮度和所有杂曜',
            'sihua_profile':sihua_profile,'matches':not issues,'differences':issues}
