"""合成开发自测：不是测试组独立真值，也不是模型准确率。"""
from copy import deepcopy
from checker_v2 import run_checker_v2, InputError
import json
from pathlib import Path


def make_fixture():
    task={'task_id':'DEMO-TASK-V2','customer_id':'C001','scope':'CLOUD_SERVER',
          'incident_id':'INC-001','incident_start':'2026-06-01T10:00:00Z','incident_end':'2026-06-01T11:30:00Z'}
    def record(source,eid,**kwargs):
        return dict(evidence_id=eid,citation='demo://'+eid,source_type=source,
                    customer_id='C001',scope='CLOUD_SERVER',version='V1',
                    effective_from='2026-01-01T00:00:00Z',effective_to='2026-12-31T23:59:59Z',**kwargs)
    contract=record('CRM_CONTRACT_DB','E-CONTRACT',rule_id='RULE-001',
                    terms={'allows_compensation':True,'min_incident_minutes':30,
                           'deduct_maintenance':True,'exceptions':['CLIENT_CONFIG_ERROR','FORCE_MAJEURE']})
    material={
        'CRM_CONTRACT_DB':[contract],
        'PLAN_DB':[record('PLAN_DB','E-PLAN',customer_tier='VIP',plan_type='Enterprise_Pro')],
        'MONITORING_SYSTEM':[record('MONITORING_SYSTEM','E-INCIDENT',incident_id='INC-001',start=task['incident_start'],end=task['incident_end'])],
        'MAINTENANCE_CALENDAR':[record('MAINTENANCE_CALENDAR','E-MAINT-1',planned=True,start='2026-06-01T10:00:00Z',end='2026-06-01T10:40:00Z')],
        'TICKET_SYSTEM':[record('TICKET_SYSTEM','E-TICKET',incident_id='INC-001',cause_codes=['PROVIDER_FAILURE'])],
        'BACKEND_LOGS':[record('BACKEND_LOGS','E-LOG',incident_id='INC-001',cause_codes=['PROVIDER_FAILURE'])]}
    responses={}
    for source,records in material.items():
        responses[source]=dict(task, evidence_id='Q-'+source,citation='demo://query/'+source,
                               source_type=source,tool_status='SUCCESS',pagination_complete=True,
                               fetched_at='2026-06-02T00:00:00Z',records=records)
    return task,responses


def run_checks(rules):
    """给每种边界单独保存结果，方便开会解释。"""
    table=[]
    def check(name,change,expected,extra=None):
        task,responses=make_fixture()
        change(task,responses)
        before=deepcopy((task,responses,rules))
        result=run_checker_v2(task,responses,rules)
        assert result['current_decision'] is expected,(name,result)
        assert before==(task,responses,rules),'函数修改了输入'
        assert result==run_checker_v2(task,responses,rules),'结果不确定'
        if extra:extra(result)
        table.append({'case':name,'expected':expected,'actual':result['current_decision'],'passed':True})
    def rec(r,source):return r[source]['records'][0]
    def setv(source,key,value):return lambda t,r:r[source].update({key:value})
    def contract_terms(key,value):return lambda t,r:rec(r,'CRM_CONTRACT_DB')['terms'].update({key:value})
    check('VIP正常：90扣40得到50',lambda t,r:None,True,lambda x:assert_net(x,50))
    check('刚好30分钟',lambda t,r:rec(r,'MAINTENANCE_CALENDAR').update(end='2026-06-01T11:00:00Z'),True,lambda x:assert_net(x,30))
    check('净时长20分钟',lambda t,r:rec(r,'MAINTENANCE_CALENDAR').update(end='2026-06-01T11:10:00Z'),False)
    check('差一秒不达标',lambda t,r:rec(r,'MAINTENANCE_CALENDAR').update(end='2026-06-01T11:00:01Z'),False)
    check('重叠维护不重复扣',lambda t,r:r['MAINTENANCE_CALENDAR']['records'].append(dict(rec(r,'MAINTENANCE_CALENDAR'),evidence_id='E-MAINT-2',start='2026-06-01T10:20:00Z',end='2026-06-01T10:50:00Z')),True,lambda x:assert_net(x,40))
    check('维护跨出故障区间只扣交集',lambda t,r:rec(r,'MAINTENANCE_CALENDAR').update(start='2026-06-01T09:00:00Z',end='2026-06-01T10:40:00Z'),True,lambda x:assert_net(x,50))
    check('完整维护空结果可不扣',setv('MAINTENANCE_CALENDAR','records',[]),True,lambda x:assert_net(x,90))
    check('非计划维护不扣',lambda t,r:rec(r,'MAINTENANCE_CALENDAR').update(planned=False),True,lambda x:assert_net(x,90))
    check('维护分页未完',setv('MAINTENANCE_CALENDAR','pagination_complete',False),None)
    check('维护时间反向',lambda t,r:rec(r,'MAINTENANCE_CALENDAR').update(end='2026-06-01T09:00:00Z'),None)
    check('维护缺时间',lambda t,r:rec(r,'MAINTENANCE_CALENDAR').pop('start'),None)
    check('合同未查询',lambda t,r:r.pop('CRM_CONTRACT_DB'),None)
    check('合同超时',setv('CRM_CONTRACT_DB','tool_status','TIMEOUT'),None)
    check('合同403',setv('CRM_CONTRACT_DB','tool_status','ACCESS_DENIED'),None)
    check('合同查询错客户',setv('CRM_CONTRACT_DB','customer_id','C002'),None)
    check('合同空第一页不回退',lambda t,r:r['CRM_CONTRACT_DB'].update(records=[],pagination_complete=False),None)
    check('合同查询时间错',setv('CRM_CONTRACT_DB','incident_start','2026-06-02T10:00:00Z'),None)
    check('合同回执缺抓取时间',lambda t,r:r['CRM_CONTRACT_DB'].pop('fetched_at'),None)
    check('完整合同空结果：VIP回退',setv('CRM_CONTRACT_DB','records',[]),True)
    check('完整查询仅过期合同：回退',lambda t,r:rec(r,'CRM_CONTRACT_DB').update(effective_to='2026-05-01T00:00:00Z'),True)
    check('完整查询仅不适用客户记录',lambda t,r:rec(r,'CRM_CONTRACT_DB').update(customer_id='C002'),True)
    check('合同缺有效期不能当不存在',lambda t,r:rec(r,'CRM_CONTRACT_DB').pop('effective_to'),None)
    check('合同缺客户不能当不存在',lambda t,r:rec(r,'CRM_CONTRACT_DB').pop('customer_id'),None)
    check('合同明确禁止优先于通用',contract_terms('allows_compensation',False),False)
    check('合同禁止无需后续资料',lambda t,r:(rec(r,'CRM_CONTRACT_DB')['terms'].update(allows_compensation=False),r.pop('MONITORING_SYSTEM'),r.pop('TICKET_SYSTEM')),False)
    check('合同没有维护约定不自动填',lambda t,r:rec(r,'CRM_CONTRACT_DB')['terms'].pop('deduct_maintenance'),None)
    check('合同缺免责清单不自动填',lambda t,r:rec(r,'CRM_CONTRACT_DB')['terms'].pop('exceptions'),None)
    check('布尔值门槛无效',contract_terms('min_incident_minutes',True),None)
    check('文字门槛无效',contract_terms('min_incident_minutes','30'),None)
    check('未知规则',lambda t,r:rec(r,'CRM_CONTRACT_DB').update(rule_id='NOT-A-RULE'),None)
    check('合同与身份范围不符',lambda t,r:rec(r,'PLAN_DB').update(customer_tier='STANDARD'),None)
    check('两份同时有效合同',lambda t,r:r['CRM_CONTRACT_DB']['records'].append(dict(rec(r,'CRM_CONTRACT_DB'),evidence_id='E-CONTRACT-2',version='V2')),None)
    def future(t,r):
        old=rec(r,'CRM_CONTRACT_DB')
        newer=deepcopy(old);newer.update(evidence_id='E-CONTRACT-2',version='V2',effective_from='2026-07-01T00:00:00Z')
        newer['terms']['allows_compensation']=False
        r['CRM_CONTRACT_DB']['records'].append(newer)
    check('新版本故障后生效仍用旧版本',future,True)
    check('故障跨有效期边界',lambda t,r:rec(r,'CRM_CONTRACT_DB').update(effective_to='2026-06-01T11:00:00Z'),None)
    check('查询时已过期但故障时有效',lambda t,r:r['CRM_CONTRACT_DB'].update(fetched_at='2027-02-01T00:00:00Z'),True)
    check('监控缺失',lambda t,r:r.pop('MONITORING_SYSTEM'),None)
    check('故障编号不一致',lambda t,r:rec(r,'MONITORING_SYSTEM').update(incident_id='INC-999'),None)
    check('工单缺失',lambda t,r:r.pop('TICKET_SYSTEM'),None)
    check('日志缺失',lambda t,r:r.pop('BACKEND_LOGS'),None)
    check('免责原因明确',lambda t,r:[rec(r,s).update(cause_codes=['CLIENT_CONFIG_ERROR']) for s in ['TICKET_SYSTEM','BACKEND_LOGS']],False)
    check('工单日志根因冲突',lambda t,r:rec(r,'BACKEND_LOGS').update(cause_codes=['CLIENT_CONFIG_ERROR']),None)
    check('空根因不当作没有免责',lambda t,r:rec(r,'TICKET_SYSTEM').update(cause_codes=[]),None)
    def standard(t,r):
        r['CRM_CONTRACT_DB']['records']=[];rec(r,'PLAN_DB').update(customer_tier='STANDARD',plan_type='Basic')
    check('普通客户无合同通用规则',standard,True)
    def special(t,r,rid,tier,plan,source):
        rec(r,'PLAN_DB').update(customer_tier=tier,plan_type=plan)
        rec(r,'CRM_CONTRACT_DB').update(rule_id=rid)
        base=deepcopy(r['PLAN_DB']);base.update(source_type=source,evidence_id='Q-SPECIAL')
        base['records'][0].update(source_type=source,evidence_id='E-SPECIAL',eligible=True)
        r[source]=base
    check('金融专门身份资料齐全',lambda t,r:special(t,r,'RULE-003','FINANCE','FINANCE_ZONE','FINANCE_ZONE_DB'),True)
    check('KA专门身份资料齐全',lambda t,r:special(t,r,'RULE-004','KA_STRATEGIC','Custom_Dedicated','KA_CLIENT_DB'),True)
    check('试用明确免赔',lambda t,r:special(t,r,'RULE-005','TRIAL','Free_Tier','TRIAL_ACCOUNTS_DB'),False)
    check('金融缺专门身份资料',lambda t,r:(rec(r,'PLAN_DB').update(customer_tier='FINANCE',plan_type='FINANCE_ZONE'),rec(r,'CRM_CONTRACT_DB').update(rule_id='RULE-003')),None)
    check('陌生根因不自动放行',lambda t,r:[rec(r,s).update(cause_codes=['UNKNOWN']) for s in ['TICKET_SYSTEM','BACKEND_LOGS']],None)
    check('通配免责不自动放行',contract_terms('exceptions',['ALL_EXCEPTIONS']),None)
    # 结构错误另报错，不伪装成一次正常业务判断。
    for name,modify in [('重复证据编号',lambda t,r:rec(r,'PLAN_DB').update(evidence_id='E-CONTRACT')),
                        ('任务无时区',lambda t,r:t.update(incident_start='2026-06-01T10:00:00'))]:
        t,r=make_fixture();modify(t,r)
        try:run_checker_v2(t,r,rules)
        except InputError:table.append({'case':name,'expected':'InputError','actual':'InputError','passed':True})
        else:raise AssertionError(name)
    return table


def assert_net(result,expected):
    assert result['duration']['net_minutes']==expected,result['duration']


if __name__=='__main__':
    rules=json.loads(Path('rules.json').read_text(encoding='utf-8'))
    print(json.dumps(run_checks(rules),ensure_ascii=False,indent=2))
