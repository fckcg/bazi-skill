"""Source-gated parallel review of traditional methods; no event predictions."""
import argparse
import hashlib
from itertools import combinations
import json
import sys
from pathlib import Path

REGISTRY = Path(__file__).resolve().parent.parent/'references/method-registry.json'
GAN = '甲乙丙丁戊己庚辛壬癸'
ZHI = '子丑寅卯辰巳午未申酉戌亥'
ELEMENT = dict(zip(GAN, ['木','木','火','火','土','土','金','金','水','水']))
CYCLE = ['木','火','土','金','水']
HIDDEN = {'子':'癸','丑':'己癸辛','寅':'甲丙戊','卯':'乙','辰':'戊乙癸','巳':'丙戊庚',
          '午':'丁己','未':'己丁乙','申':'庚壬戊','酉':'辛','戌':'戊辛丁','亥':'壬甲'}
LABELS = ['年柱','月柱','日柱','时柱']


def validate_registry(registry):
    if not isinstance(registry,dict) or not isinstance(registry.get('profiles'),list) or not isinstance(registry.get('rules'),list):
        raise ValueError('Invalid method registry structure.')
    profiles=registry['profiles'];rules=registry['rules']
    lookup={}
    for p in profiles:
        if not isinstance(p,dict) or not isinstance(p.get('id'),str) or p['id'] in lookup:
            raise ValueError('Invalid or duplicate method profile id.')
        if not isinstance(p.get('verified_rule_ids'),list) or not isinstance(p.get('sources'),list):
            raise ValueError('Profile lacks rule ids or sources.')
        lookup[p['id']]=p
    ids=set()
    for rule in rules:
        if not isinstance(rule,dict) or not isinstance(rule.get('id'),str) or rule['id'] in ids:
            raise ValueError('Invalid or duplicate rule id.')
        ids.add(rule['id'])
        owner=lookup.get(rule.get('profile'))
        if owner is None or owner.get('source_status')!='text_excerpt_checked' or rule.get('evidence_status')!='text_excerpt_checked':
            raise ValueError('Unverified author rule cannot be enabled.')
        if not rule.get('locator') or not rule.get('scope') or not isinstance(rule.get('source_url'),str) or not rule['source_url'].startswith('https://'):
            raise ValueError('Active rule requires an HTTPS source, locator and scope.')
        if rule['source_url'] not in [x.get('url') for x in owner['sources'] if isinstance(x,dict)]:
            raise ValueError('Rule source is not registered to its author.')
        if rule['id'] not in owner['verified_rule_ids']:
            raise ValueError('Rule not registered to owner.')
    for p in profiles:
        actual={r['id'] for r in rules if r['profile']==p['id']}
        if set(p['verified_rule_ids'])!=actual:
            raise ValueError('Dangling or misattributed rule id.')
    return registry


def load_registry():
    return validate_registry(json.loads(REGISTRY.read_text(encoding='utf-8')))



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
    elif action=='support_control_review':
        finding={'supporting_visible_gods':[x for x in f['visible_gods'] if x['god'] in ('比肩','劫财','正印','偏印')],
                 'draining_or_controlling_visible_gods':[x for x in f['visible_gods'] if x['god'] not in ('比肩','劫财','正印','偏印')],
                 'strength_conclusion':None,'note':'先区分扶抑的对象和依据，不因出现某类十神就定喜忌。'}
    elif action=='monthly_day_allocation':
        finding={'month_branch':f['month_branch'],'hidden_gods':f['month_hidden_gods'],
                 'mechanical_fixed_day_allocation':False,'note':'该段反对机械藏干分日；不改变历法月柱。'}
    elif action=='peer_review':
        finding={'visible_peers':[x for x in f['visible_gods'] if x['god'] in ('比肩','劫财')],
                 'hidden_peers':[{'position':LABELS[i],'stem':g,'god':ten_god(f['day_master'],g)}
                                for i,pillar in enumerate(f['pillars']) for g in HIDDEN[pillar[1]]
                                if ELEMENT[g]==ELEMENT[f['day_master']]],
                 'note':'只核对构成，不推断兄弟关系、争财或个性。'}
    elif action=='month_appearance_priority':
        hidden=f['month_hidden_gods'];main=hidden[0]
        visible=[x for x in hidden if f['stem_presence'][x['stem']]['visible']]
        if main['god'] in ('比肩','劫财'):
            path='outside_eight_requires_separate_review';candidates=[]
        elif main in visible:
            path='main_qi_visible';candidates=[main]
        elif visible:
            path='other_hidden_qi_visible';candidates=[x for x in visible if x['god'] not in ('比肩','劫财')]
        else:
            path='none_visible_requires_strength_review';candidates=[]
        finding={'review_path':path,'main_qi':main,'visible_month_hidden_gods':visible,
                 'candidate_gods':candidates,'final_format':None,
                 'note':'候选检查顺序不等于成格；本气比劫须另查禄刃等条件。'}
    elif action=='seasonal_states':
        states={'春':{'木':'旺','火':'相','水':'休','金':'囚','土':'死'},
                '夏':{'火':'旺','土':'相','木':'休','水':'囚','金':'死'},
                '秋':{'金':'旺','水':'相','土':'休','火':'囚','木':'死'},
                '冬':{'水':'旺','木':'相','金':'休','土':'囚','火':'死'}}
        special=f['month_branch'] in '辰戌丑未'
        finding={'season':f['season'],'states':None if special else states[f['season']],
                 'earth_transition_convention_requires_review':special,
                 'note':'旺相休囚死仅为传统术语，不代表身体、寿命或现实事件；土寄旺时期不自动按整月定。'}
    else:raise ValueError('Unimplemented rule action: '+action)
    return {'rule_id':rule['id'],'locator':rule['locator'],'scope':rule['scope'],
            'source_url':rule.get('source_url'),'finding':finding,'type':'traditional_structure_review','predictive_validity':'not_established'}


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
    if not isinstance(chart_data,dict) or not isinstance(chart_data.get('central'),dict):
        raise ValueError('Input must be chart.py JSON with central.pillars.')
    central=chart_data['central']
    f=facts(central.get('pillars'))
    candidates=chart_data.get('candidates',[])
    if not isinstance(candidates,list) or any(not isinstance(c,dict) for c in candidates):
        raise ValueError('Candidates must be a list of chart objects.')
    if not isinstance(chart_data.get('conventions',{}),dict):
        raise ValueError('Time conventions must be an object.')
    if not isinstance(chart_data.get('near_solar_terms_requiring_review',[]),list):
        raise ValueError('Near solar terms must be a list.')
    unique=[];seen=set()
    for c in candidates:
        cf=facts(c.get('pillars'));key=tuple(cf['pillars'])
        if key not in seen:unique.append(cf);seen.add(key)
    if candidates and tuple(f['pillars']) not in seen:
        raise ValueError('Central chart must appear among the candidates.')
    stable=chart_data.get('pillars_stable_in_scanned_range')
    if stable is not None and not isinstance(stable,bool):
        raise ValueError('Chart stability flag must be boolean.')
    if stable is True and len(unique)>1:
        raise ValueError('Stability flag conflicts with multiple distinct candidates.')
    if stable is False and len(unique)<2:
        raise ValueError('Ambiguous chart must contain multiple distinct candidates.')
    ambiguous=len(unique)>1
    rule_inputs=unique if unique else [f]
    profiles=select_profiles(selection,registry)
    results=[]
    for p in profiles:
        rules=[r for r in registry['rules'] if r['id'] in p['verified_rule_ids']]
        evaluations=[]
        for rule in rules:
            item=inspect_rule(rule,f)
            item['candidate_findings']=[{'pillars':cf['pillars'],'finding':inspect_rule(rule,cf)['finding']} for cf in rule_inputs]
            findings=[x['finding'] for x in item['candidate_findings']]
            item['stable_across_candidates']=all(v==findings[0] for v in findings)
            evaluations.append(item)
        results.append({'id':p['id'],'author':p['author'],'focus':p['focus'],
                        'source_status':p['source_status'],'sources':p['sources'],
                        'project_checklist':p['project_checklist'],
                        'project_evidence':project_evidence(p, chart_data, f),
                        'rules':evaluations,
                        'unverified_attribution_withheld':not bool(rules),
                        'limit':p['attribution_limit']})
    candidate_facts=unique if ambiguous else []
    selected_ids={p['id'] for p in profiles}
    disagreements=[]
    if {'chen-suan','ren-tieqiao'} <= selected_ids:
        disagreements.append({'topic':'藏干分日与人元司令','profiles':['chen-suan','ren-tieqiao'],
                              'rule_ids':['CHEN-002','REN-001'],
                              'note':'所核对段落在分日解释上的立场不同；只提示理论约定差异，不改变历法月柱或用多数裁决。'})
    return {'methods_version':registry['version'],'chart_version':chart_data.get('version'),
            'registry_sha256':hashlib.sha256(REGISTRY.read_bytes()).hexdigest(),
            'time_conventions_inherited':chart_data.get('conventions'),
            'central_facts':f,'candidate_facts':candidate_facts,
            'birth_uncertainty_minutes':chart_data.get('conventions',{}).get('uncertainty_minutes'),
            'near_solar_terms_requiring_review':chart_data.get('near_solar_terms_requiring_review',[]),
            'ambiguous_chart':ambiguous,'method_results':results,
            'comparison':{'mode':'parallel','do_not_merge':['格局用神','扶抑喜用','调候需求','病药制化'],
                          'majority_vote':False,'prediction_probability':None,'method_disagreements':disagreements},
            'warnings':['没有核对正文的作者只提供项目研究清单，不输出所谓独门结论。',
                        '时柱有多个候选时，不能用某位作者的解释强行确定出生时间。',
                        '各方法解释一致不能推导预测准确率；本输出不评定能力、心理疾病或未来事件。']}


def render_markdown(review):
    """Readable review, preserving attribution and candidate-dependent results."""
    def cell(value):
        return str(value).replace('|', '／').replace('\n', ' ')
    def friendly(value):
        if value is None:return '未判定'
        if isinstance(value,bool):return '是' if value else '否'
        if isinstance(value,list):return '、'.join(friendly(x) for x in value) or '无'
        if isinstance(value,dict):
            names={'position':'柱位','branch':'地支','branches':'地支','stem':'天干','stems':'藏干','god':'十神','visible':'透干','hidden':'藏干'}
            return '；'.join(names.get(k,k)+'：'+friendly(v) for k,v in value.items()) or '无'
        paths={'main_qi_visible':'月令本气透干','other_hidden_qi_visible':'本气未透、其他藏干透出','none_visible_requires_strength_review':'皆未透，须继续核对','outside_eight_requires_separate_review':'比劫月令，不直接套八格'}
        return paths.get(str(value),cell(value))
    f=review['central_facts']
    lines=['# 传统方法并列核对', '',
           '中央时刻四柱：'+'　'.join(f['pillars'])+'。日主：'+f['day_master']+'。', '',
           '这是结构事实与所列传统文本的核对，不是事件预测或人格测评。', '',
           '| 柱位 | 干支 |', '|---|---|']
    lines.extend('| '+a+' | '+b+' |' for a,b in zip(LABELS,f['pillars']))
    lines += ['', '## 输入确定性', '',
              '报告的出生时间误差（分钟）：'+str(review['birth_uncertainty_minutes'])+'。这只是输入参数，不代表出生记录已认证。',
              '多个候选盘：'+('有，以下分别检查。' if review['ambiguous_chart'] else '当前提供的候选中没有差异；仍需确认实际时间误差。')]
    for cf in review['candidate_facts']:
        lines.append('- 候选：'+'　'.join(cf['pillars']))
    if review['near_solar_terms_requiring_review']:
        lines.append('- 靠近交节，需复核官方时刻。')
    for profile in review['method_results']:
        lines += ['', '## '+cell(profile['author'])+'：'+cell(profile['focus']), '',
                  '来源状态：'+{'text_excerpt_checked':'所列原文段落已核对','bibliography_checked':'书目已核对，规则正文待补','bibliography_provisional':'书目仍待更可靠来源'}.get(profile['source_status'],cell(profile['source_status']))+'。', '',
                  '项目核对清单：'+cell(profile['project_checklist'])]
        if profile['unverified_attribution_withheld']:
            lines += ['', '该模块的具体原文规则尚未核对，不输出作者独门结论。']
        for rule in profile['rules']:
            lines += ['', '### '+cell(rule['rule_id'])+'：'+cell(rule['locator']), '',
                      cell(rule['scope']), '',
                      '来源：[所列段落](<'+rule['source_url']+'>)。',
                      '在输入候选之间是否一致：'+('一致。' if rule['stable_across_candidates'] else '有差异，不能只采用中央盘。')]
            for entry in rule['candidate_findings']:
                lines += ['', '**'+'　'.join(entry['pillars'])+'**', '']
                finding=entry['finding']
                for key,value in finding.items():
                    if key=='note':continue
                    labels={'main_qi':'月令本气','hidden_gods':'月令藏干十神','same_element_roots':'同五行根气',
                            'requested_stems':'原文所讨论天干的位置','candidate_gods':'取格检查候选',
                            'states':'传统季节状态','review_path':'检查路径','visible_peers':'透干比劫',
                            'hidden_peers':'藏干比劫','separate_fields':'分开讨论的问题','review_steps':'核对步骤',
                            'strength_conclusion':'旺衰结论','final_format':'最终格局',
                            'mechanical_fixed_day_allocation':'机械藏干分日',
                            'earth_transition_convention_requires_review':'土寄旺约定需复核',
                            'supporting_visible_gods':'透干生扶关系','draining_or_controlling_visible_gods':'透干克泄耗关系',
                            'applicable':'本条适用','month_branch':'月支','season':'季节','chapter':'篇章',
                            'visible_month_hidden_gods':'月令藏干的透出情况'}
                    rendered=friendly(value)
                    lines.append('- '+labels.get(key,key)+'：'+rendered)
                lines.append('- 说明：'+cell(finding.get('note','')))
        lines += ['', '书目及版本：']
        for source in profile['sources']:
            lines.append('- [来源](<'+source['url']+'>)：'+cell(source['locator'])+'。'+cell(source['edition_note']))
    lines += ['', '## 方法分歧', '']
    for item in review['comparison']['method_disagreements']:
        lines.append('- '+cell(item['topic'])+'：'+cell(item['note']))
    if not review['comparison']['method_disagreements']:
        lines.append('本次没有列出的特定分歧，不表示这些方法已证明一致。')
    lines += ['', '不以作者数量投票，不将解释一致换算成概率。', '']
    return '\n'.join(lines)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    modes=p.add_mutually_exclusive_group(required=True)
    modes.add_argument('--list',action='store_true')
    modes.add_argument('--chart-json',type=Path)
    p.add_argument('--select',default='all',help='Comma-separated author names or ids, or all')
    p.add_argument('--format',choices=['json','markdown'],default='json')
    a=p.parse_args()
    try:
        if a.list and a.format=='markdown':
            raise ValueError('--list supports JSON only.')
        result=load_registry()['profiles'] if a.list else review_chart(json.loads(sys.stdin.read() if str(a.chart_json)=='-' else a.chart_json.read_text(encoding='utf-8-sig')),a.select)
    except (ValueError,OSError) as e:p.error(str(e))
    print(render_markdown(result) if a.format=='markdown' else json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
