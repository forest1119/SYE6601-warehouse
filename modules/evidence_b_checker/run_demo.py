"""不联网的一键演示：生成输入、检查结果、评分结果和给Loop看的补证前后样例。"""
from copy import deepcopy
import sys
from pathlib import Path
from checker_api import check_payload,make_score_snapshot,read_json,write_json
from test_checker_v2 import make_fixture
sys.path.insert(0,str(Path(__file__).resolve().parent/'vendor'))
from confidence_a import score_snapshot


def run_demo(folder=None):
    base=Path(__file__).resolve().parent
    target=Path(folder) if folder is not None else base/'examples'
    rules=read_json(base/'rules.json')
    summary=[]
    for index,name in enumerate(['normal','denied','missing_contract','access_denied','cause_conflict']):
        task,responses=make_fixture()
        if name=='denied':responses['CRM_CONTRACT_DB']['records'][0]['terms']['allows_compensation']=False
        if name=='missing_contract':responses.pop('CRM_CONTRACT_DB')
        if name=='access_denied':responses['CRM_CONTRACT_DB'].update(tool_status='ACCESS_DENIED',records=[])
        if name=='cause_conflict':responses['BACKEND_LOGS']['records'][0]['cause_codes']=['CLIENT_CONFIG_ERROR']
        payload={'task':task,'responses':responses,'rules':rules}
        result=check_payload(payload)
        # RUNNING代表没有冒充Loop已经结束或转人工。
        snap=make_score_snapshot(result,'DEMO-RUN-'+name,'DEMO-SNAPSHOT-'+str(index))
        card=score_snapshot(snap)
        write_json(target/(name+'_input.json'),payload)
        write_json(target/(name+'_checker.json'),result)
        write_json(target/(name+'_snapshot.json'),snap)
        write_json(target/(name+'_scorecard.json'),card)
        summary.append({'case':name,'decision':result['checker_decision'],'score':card['score'],
                        'may_present_definitive_decision':card['may_present_definitive_decision'],
                        'gap_count':len(result['gaps'])})
    # 这只是手动输入两个完整快照的示范，不模拟已经发生的真实工具调用。
    write_json(target/'supplement_example.json',{
        'description':'先把missing_contract_input交给Checker，再把normal_input作为补齐合同后的完整快照；非自动Loop执行日志。',
        'before':'missing_contract_checker.json','after':'normal_checker.json'})
    write_json(target/'summary.json',summary)
    return summary

if __name__=='__main__':
    for row in run_demo():print(row)
