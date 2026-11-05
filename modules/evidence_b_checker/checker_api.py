"""面向Loop和评分组的入口：本文件仅使用Python标准库。"""
from copy import deepcopy
import json
import math
from pathlib import Path
from checker_v2 import run_checker_v2, InputError

CHECK_NAMES=('source_allowed','scope_valid','version_valid','time_valid','query_sufficient')

def ensure_json_data(value,path='$'):
    """输入必须是真正JSON数据；拒绝NaN、Infinity及非文字字典键。"""
    if value is None or type(value) in (str,bool,int):
        return
    if type(value) is float:
        if not math.isfinite(value):raise InputError(path+' 不允许NaN或Infinity')
        return
    if isinstance(value,list):
        for i,item in enumerate(value):ensure_json_data(item,f'{path}[{i}]')
        return
    if isinstance(value,dict):
        for key,item in value.items():
            if not isinstance(key,str):raise InputError(path+' 的字段名必须是文字')
            ensure_json_data(item,path+'.'+key)
        return
    raise InputError(path+' 包含不能保存为JSON的类型')


def check_payload(payload):
    """Loop每次传完整快照：task、responses、rules。缺证不要求先凑齐再调用。"""
    ensure_json_data(payload)
    if not isinstance(payload,dict) or set(payload)!= {'task','responses','rules'}:
        raise InputError('最外层请填写且只填写 task、responses、rules 三个字段')
    result=run_checker_v2(payload['task'],payload['responses'],payload['rules'])
    result['schema_version']='02B-handoff-0.3-draft'
    result['integration_status']='SYNTHETIC_CONTRACT_PENDING_TEAM_MAPPING'
    # 检查声明由Checker输出，适配器不按来源名字自行推测。
    for ob in result['obligation_results']:
        established=ob['status'] in ('SUPPORT','REFUTE')
        ob['checks']=dict.fromkeys(CHECK_NAMES,True if established else None)
        ob['must_verify']=False
        ob['applicability']='APPLICABLE'
        ob['applicability_reason']='当前补偿流程中的检查项；未知与跳过均保留，不冒充不适用。'
    # 找到逻辑上真正卡住的第一项，避免Loop被后续“未检查”项误导。
    blockers=[ob for ob in result['obligation_results']
              if ob['required_for_decision'] and ob['status'] in ('UNKNOWN','CONFLICT')]
    primary=next((ob for ob in blockers if ob['reason_codes']!=['NOT_CHECKED']),None)
    dependency=primary['obligation_id'] if primary else None
    result['gaps']=[]
    for ob in blockers:
        gap=deepcopy(ob)
        gap['blocked_by']=[dependency] if dependency and ob['obligation_id']!=dependency else []
        gap['ready_for_lookup']=not gap['blocked_by'] and bool(ob['required_sources'])
        result['gaps'].append(gap)
    return result


def make_score_snapshot(result,run_id,snapshot_id,process_state='RUNNING',stop_reason=None):
    """明确转换到07A草案。流程状态由调用方给，不把Checker结果当Loop已结束。"""
    if result.get('schema_version')!='02B-handoff-0.3-draft':
        raise InputError('请先用check_payload生成新结果，不要混用旧版输出')
    for value in (run_id,snapshot_id):
        if not isinstance(value,str) or not value.strip():raise InputError('运行和快照编号不能为空')
    if process_state not in ('RUNNING','COMPLETED','ESCALATED'):
        raise InputError('流程状态无效')
    if process_state!='RUNNING' and (not isinstance(stop_reason,str) or not stop_reason.strip()):
        raise InputError('停止或升级需要stop_reason说明')
    if process_state=='ESCALATED' and result['current_decision'] is not None:
        raise InputError('当前07A草案不支持明确结论同时升级；需与评分组协商')
    # 构建完整索引，再按引用选择，包含空结果回执和业务规则原文。
    evidence={}
    for source,response in result['raw_responses'].items():
        for record in [response]+response['records']:
            evidence[record['evidence_id']]={'evidence_id':record['evidence_id'],
                'source_type':source,'citation':record['citation']}
    for policy in result['used_policy_evidence']:
        evidence[policy['evidence_id']]={'evidence_id':policy['evidence_id'],
            'source_type':'BUSINESS_RULES','citation':policy['citation']}
    obs=[];used=set()
    for original in result['obligation_results']:
        ids=original['evidence_ids']
        if any(eid not in evidence for eid in ids):raise InputError('存在找不到原记录的引用')
        used.update(ids)
        # 非必要的跳过项仍留在分母中，不通过删除它来虚增评分。
        obs.append({k:deepcopy(original[k]) for k in ['obligation_id','statement','applicability',
            'applicability_reason','required_for_decision','must_verify','status','checks',
            'evidence_ids','reason_codes','reason']})
        obs[-1]['rule_id']=result['selected_rule_id'] or 'PENDING-RULE-SELECTION'
    return {'schema_version':'0.1-draft','task_id':result['task_id'],
        'run_id':run_id,'snapshot_id':snapshot_id,'rules_version':'content-'+result['rules_fingerprint'],
        'synthetic_demo':True,'checker_decision':result['checker_decision'],
        'process_state':process_state,'stop_reason':stop_reason,
        'obligations':obs,'evidence':[evidence[eid] for eid in sorted(used)]}


def read_json(path):
    """防止JSON中的重复字段被解析器悄悄覆盖。"""
    def no_duplicates(pairs):
        obj={}
        for k,v in pairs:
            if k in obj:raise InputError('JSON字段重复：'+k)
            obj[k]=v
        return obj
    def invalid_constant(value):raise InputError('JSON不允许'+value)
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'),
                          object_pairs_hook=no_duplicates,parse_constant=invalid_constant)
    except (OSError,UnicodeError,json.JSONDecodeError) as error:
        raise InputError('无法读取JSON：'+str(error)) from error


def write_json(path,value):
    ensure_json_data(value)
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
