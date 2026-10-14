"""Source-gated parallel review of traditional methods; no event predictions."""
import argparse
from itertools import combinations
import json
from pathlib import Path

REGISTRY = Path(__file__).resolve().parent.parent/'references/method-registry.json'
GAN = '甲乙丙丁戊己庚辛壬癸'
ZHI = '子丑寅卯辰巳午未申酉戌亥'
ELEMENT = dict(zip(GAN, ['木','木','火','火','土','土','金','金','水','水']))
CYCLE = ['木','火','土','金','水']
HIDDEN = {'子':'癸','丑':'己癸辛','寅':'甲丙戊','卯':'乙','辰':'戊乙癸','巳':'丙戊庚',
          '午':'丁己','未':'己丁乙','申':'庚壬戊','酉':'辛','戌':'戊辛丁','亥':'壬甲'}
LABELS = ['年柱','月柱','日柱','时柱']


def load_registry():
    return json.loads(REGISTRY.read_text(encoding='utf-8'))


def ten_god(day, other):
    a, b = CYCLE.index(ELEMENT[day]), CYCLE.index(ELEMENT[other])
    same = GAN.index(day)%2 == GAN.index(other)%2
    diff = (b-a)%5
    return {0:('比肩','劫财'),1:('食神','伤官'),2:('偏财','正财'),
            3:('七杀','正官'),4:('偏印','正印')}[diff][0 if same else 1]


def facts(pillars):
    if not isinstance(pillars,list) or len(pillars)!=4:
        raise ValueError('Exactly four pillars are required.')
    for p in pillars:
        if not isinstance(p,str) or len(p)!=2 or p[0] not in GAN or p[1] not in ZHI:
            raise ValueError('Invalid pillar.')
        if GAN.index(p[0])%2 != ZHI.index(p[1])%2:
            raise ValueError('Pillar is not in the sexagenary cycle.')
    day = pillars[2][0]
    visible = [{'position':LABELS[i],'stem':p[0],'god':ten_god(day,p[0])} for i,p in enumerate(pillars) if i!=2]
    roots = [{'position':LABELS[i],'branch':p[1],'stems':[s for s in HIDDEN[p[1]] if ELEMENT[s]==ELEMENT[day]]}
             for i,p in enumerate(pillars) if any(ELEMENT[s]==ELEMENT[day] for s in HIDDEN[p[1]])]
    presence={s:{'visible':[LABELS[i] for i,p in enumerate(pillars) if p[0]==s],
                 'hidden':[LABELS[i] for i,p in enumerate(pillars) if s in HIDDEN[p[1]]]}
              for s in GAN}
    groups={'冲':['子午','丑未','寅申','卯酉','辰戌','巳亥'],
            '六合':['子丑','寅亥','卯戌','辰酉','巳申','午未'],
            '害':['子未','丑午','寅巳','卯辰','申亥','酉戌']}
    relations=[]
    for i,j in combinations(range(4),2):
        pair=frozenset([pillars[i][1],pillars[j][1]])
        for name,pairs in groups.items():
            if pair in [frozenset(p) for p in pairs]:
                relations.append({'type':name,'positions':[LABELS[i],LABELS[j]],'branches':[pillars[i][1],pillars[j][1]],'event_meaning':None})
    month=pillars[1][1]
    season = '春' if month in '寅卯辰' else '夏' if month in '巳午未' else '秋' if month in '申酉戌' else '冬'
    return {'pillars':pillars,'day_master':day,'month_branch':month,'season':season,
            'month_hidden_gods':[{'stem':s,'god':ten_god(day,s)} for s in HIDDEN[month]],
            'visible_gods':visible,'same_element_roots':roots,'stem_presence':presence,
            'branch_relations':relations,'basis':'项目采用的常用十神与藏干约定；结构事实不等于人格或事件预测'}


def select_profiles(selection, registry):
    profiles=registry['profiles']
    if isinstance(selection,str):selection=[s.strip() for s in selection.split(',') if s.strip()]
    if not selection:raise ValueError('Select at least one method.')
    if selection==['all']:return profiles
    if 'all' in selection:raise ValueError('Use all alone, or specify individual methods.')
    lookup={p['id']:p for p in profiles}
    lookup.update({p['author']:p for p in profiles})
    selected=[];seen=set()
    for name in selection:
        if name not in lookup:raise ValueError('Unknown method: '+name)
        p=lookup[name]
        if p['id'] not in seen:selected.append(p);seen.add(p['id'])
    return selected


def inspect_rule(rule, f):
    action=rule['action']
    if action=='month_focus':
        finding={'month_branch':f['month_branch'],'hidden_gods':f['month_hidden_gods'],
                 'note':'这里只给立格检查起点，不直接宣布成格、破格或最终喜用。'}
    elif action=='root_review':
        finding={'same_element_roots':f['same_element_roots'],'season':f['season'],
                 'note':'存在根气不等于身旺；须继续检查月令、透干和制化，不给旺衰概率。'}
    elif action=='separate_questions':
        finding={'separate_fields':['格局中心','扶抑取用','调候取用','病药制化','专旺/通关适用条件'],
                 'note':'保留原文与评注的不同定义，不自动融合。'}
    elif action=='wu_hai_review':
        applies=f['day_master']=='戊' and f['month_branch']=='亥'
        finding={'applicable':applies,'chapter':'三冬戊土：十月段',
                 'requested_stems':{s:f['stem_presence'][s] for s in '甲丙'} if applies else {},
                 'note':'本条只覆盖戊日亥月；其他日月须查相应原文，不能套用。'}
    elif action=='conditional_review':
        finding={'review_steps':['明确要讨论的结构目标','论证阻碍该目标的生克关系','检查制化路径及副作用'],
                 'note':'此处病药是命理术语；不认定个人疾病，也不自动指定用神。'}
    else:raise ValueError('Unimplemented rule action: '+action)
    return {'rule_id':rule['id'],'locator':rule['locator'],'scope':rule['scope'],
            'finding':finding,'type':'traditional_structure_review','predictive_validity':'not_established'}


def project_evidence(profile, chart_data, f):
    """Shared project facts for research; explicitly not an author's verified algorithm."""
    ident=profile['id']
    if ident in ('shen-xiaozhan','chen-suan'):
        data={'month_hidden_gods':f['month_hidden_gods'],'visible_gods':f['visible_gods']}
    elif ident in ('ren-tieqiao','wei-qianli'):
        data={'season':f['season'],'same_element_roots':f['same_element_roots'],'visible_gods':f['visible_gods']}
    elif ident in ('yu-chuntai','xu-lewu'):
        data={'day_master':f['day_master'],'month_branch':f['month_branch'],'season':f['season'],'stem_presence':f['stem_presence']}
    elif ident in ('liang-xiangrun','zhong-yiming'):
        data={'natal_pillars':f['pillars'],'yun':chart_data['central'].get('yun'),
              'note':'大运仅是所选约定下的程序结果，不是作者已经核对的流年断法。'}
    elif ident=='duan-jianye':
        data={'palace_labels':dict(zip(LABELS,f['pillars'])),'branch_relations':f['branch_relations'],
              'note':'仅整理宫位输入，不自动推导宾主、做功或现实事件。'}
    elif ident in ('zou-wenyao','wu-junmin'):
        data={'time_conventions':chart_data.get('conventions'),'candidates':chart_data.get('candidates'),
              'near_terms':chart_data.get('near_solar_terms_requiring_review')}
    elif ident=='he-jianzhong':
        data={'visible_gods':f['visible_gods'],'actual_observations_needed':['本人描述的具体场景','行为例子','环境因素'],
              'personality_assessment':None}
    else:
        data={'natal_pillars':f['pillars'],'source_status':profile['source_status'],
              'next_step':'查原书具体章节与版本，再将结构线索登记为作者规则。'}
    return {'origin':'project_shared_facts_not_author_rule','data':data}


def review_chart(chart_data, selection='all'):
    registry=load_registry()
    try:central=chart_data['central'];f=facts(central['pillars'])
    except (KeyError,TypeError) as e:raise ValueError('Input must be chart.py JSON with central.pillars.') from e
    candidates=chart_data.get('candidates',[])
    ambiguous=chart_data.get('pillars_stable_in_scanned_range') is False or len(candidates)>1
    profiles=select_profiles(selection,registry)
    results=[]
    for p in profiles:
        rules=[r for r in registry['rules'] if r['id'] in p['verified_rule_ids']]
        results.append({'id':p['id'],'author':p['author'],'focus':p['focus'],
                        'source_status':p['source_status'],'sources':p['sources'],
                        'project_checklist':p['project_checklist'],
                        'project_evidence':project_evidence(p, chart_data, f),
                        'rules':[inspect_rule(r,f) for r in rules],
                        'unverified_attribution_withheld':not bool(rules),
                        'limit':p['attribution_limit']})
    candidate_facts=[facts(c['pillars']) for c in candidates] if ambiguous else []
    return {'methods_version':registry['version'],'chart_version':chart_data.get('version'),
            'time_conventions_inherited':chart_data.get('conventions'),
            'central_facts':f,'candidate_facts':candidate_facts,
            'birth_uncertainty_minutes':chart_data.get('conventions',{}).get('uncertainty_minutes'),
            'near_solar_terms_requiring_review':chart_data.get('near_solar_terms_requiring_review',[]),
            'ambiguous_chart':ambiguous,'method_results':results,
            'comparison':{'mode':'parallel','do_not_merge':['格局用神','扶抑喜用','调候需求','病药制化'],
                          'majority_vote':False,'prediction_probability':None},
            'warnings':['没有核对正文的作者只提供项目研究清单，不输出所谓独门结论。',
                        '时柱有多个候选时，不能用某位作者的解释强行确定出生时间。',
                        '各方法解释一致不能推导预测准确率；本输出不评定能力、心理疾病或未来事件。']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    modes=p.add_mutually_exclusive_group(required=True)
    modes.add_argument('--list',action='store_true')
    modes.add_argument('--chart-json',type=Path)
    p.add_argument('--select',default='all',help='Comma-separated author names or ids, or all')
    a=p.parse_args()
    try:
        result=load_registry()['profiles'] if a.list else review_chart(json.loads(a.chart_json.read_text(encoding='utf-8-sig')),a.select)
    except (ValueError,OSError) as e:p.error(str(e))
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
