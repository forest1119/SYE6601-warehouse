"""实际调用同学的模拟函数；验证查询→适配→Checker→评分，不是生产系统。"""
import sys
from pathlib import Path
from checker_api import read_json,write_json,make_score_snapshot
from loop_b_adapter import adapt_loop_b
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'vendor'))
from loop_b_mock.mock_tools import get_customer_contract,list_maintenance
from confidence_a import score_snapshot

def sample_task(customer='002'):
    return {'task_id':'LOOPB-INTEGRATION-'+customer,'customer_id':customer,'scope':'CLOUD_SERVER',
            'incident_id':'DEMO-INCIDENT','incident_start':'2026-10-20T00:30:00Z','incident_end':'2026-10-20T02:30:00Z'}

def contract_call(customer,scenario='normal'):
    return {'request':{'customer_id':customer,'scenario':scenario,'page_token':None},
            'response':get_customer_contract(customer,scenario=scenario)}

def maintenance_call(customer,page_token=None,scenario='normal'):
    return {'request':{'customer_id':customer,'page_token':page_token,'scenario':scenario},
            'response':list_maintenance(customer,page_token=page_token,scenario=scenario)}

def integration_cases():
    for name,customer,scenario in [('contract_found','002','normal'),('contract_empty','999','normal'),
                                  ('contract_403','002','forbidden'),('contract_timeout','002','timeout'),
                                  ('contract_old','002','old_version'),('opposite_placeholder','002','conflicting_materials')]:
        yield name,sample_task(customer),{'CRM_CONTRACT_DB':[contract_call(customer,scenario)]}
    # 页序由演示脚本显式提供，不声称Loop A已经自动决策。
    yield 'maintenance_first_page',sample_task(),{'MAINTENANCE_CALENDAR':[maintenance_call('002')]}
    yield 'maintenance_all_pages',sample_task(),{'MAINTENANCE_CALENDAR':[maintenance_call('002'),maintenance_call('002','page_2')]}

def run_integration(output=None):
    folder=Path(output) if output is not None else ROOT/'loop_b_results'
    rules=read_json(ROOT/'rules.json');summary=[]
    for name,task,calls in integration_cases():
        integrated=adapt_loop_b(task,calls,rules);result=integrated['checker_result']
        snapshot=make_score_snapshot(result,'LOOPB-RUN-'+name,'LOOPB-SNAPSHOT-'+name)
        card=score_snapshot(snapshot)
        write_json(folder/(name+'.json'),integrated);write_json(folder/(name+'_scorecard.json'),card)
        summary.append({'case':name,'decision':result['checker_decision'],
                        'adapter_gaps':[g['code'] for g in integrated['adapter_gaps']],
                        'transport_status':{s:r['tool_status'] for s,r in integrated['normalized_responses'].items()},
                        'pagination_complete':{s:r['pagination_complete'] for s,r in integrated['normalized_responses'].items()}})
    write_json(folder/'summary.json',summary)
    return summary
if __name__=='__main__':
    for row in run_integration():print(row)
