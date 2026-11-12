"""Optional local PR5 integration. Requires an existing PR5 checkout, no network/API key.
Other evidence sources use PR5's synthetic provider. Only ticket retrieval is replaced.
"""
import argparse
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
from loop_b_handoff import call_with_log


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--team-root',required=True,help='Folder containing PR5 dynamic_evidence package')
    args=parser.parse_args()
    root=Path(args.team_root).resolve()
    if not (root/'dynamic_evidence'/'tools.py').is_file():
        raise SystemExit('PR5 checkout not found; choose its repository root.')
    sys.path.insert(0,str(root))
    from dynamic_evidence.tools import LoopBAdapter, TICKET
    from dynamic_evidence.cases import make_case
    from dynamic_evidence.controller import Harness
    from dynamic_evidence.mock_model import FixtureModel
    folder=Path(__file__).resolve().parent/'ticket_results'/('integration_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    folder.mkdir(parents=True)
    summaries=[]
    for case,scenario in [('DYN-01','normal'),('LATE-TICKET','late_ticket'),('BOUNDARY','boundary'),('MISSING-TICKET','missing_ticket'),('TICKET-403','forbidden'),('DYN-01','paged')]:
        task,reference=make_case(case)
        baseline=Harness(FixtureModel(),reference).run(task)
        task={**task,'scenarios':{**task.get('scenarios',{}),TICKET:scenario}}
        def reference_query(source,customer_id,scenario='normal',page_token=None):
            if customer_id!=task['customer_id']:
                raise ValueError('Reference customer mismatch')
            return reference(source,task,page_token)
        def extensions(source,request,page=None):
            if source!=TICKET:
                return reference(source,request,page)
            return call_with_log(request['task_id'],'get_ticket',
                {'customer_id':request['customer_id'],'incident_id':request['incident_id'],
                 'scenario':request.get('scenarios',{}).get(TICKET,'normal'),'page_token':page},
                folder/'calls.jsonl')['response']
        provider=LoopBAdapter(reference_query,extensions=extensions)
        bundle=Harness(FixtureModel(),provider).run(task)
        actual=bundle['answer']['recommendation'];expected=baseline['answer']['recommendation']
        if actual!=expected:
            raise AssertionError((case,scenario,expected,actual))
        name=case+'_'+scenario
        (folder/(name+'.json')).write_text(json.dumps(bundle,ensure_ascii=False,indent=2),encoding='utf-8')
        summaries.append({'case':case,'ticket_scenario':scenario,'mode':'simulated','reference_recommendation':expected,'ticket_replacement_recommendation':actual,'matched':True})
        print(name,actual,'MATCH')
    (folder/'summary.json').write_text(json.dumps({'description':'Local integration smoke test, not independent evaluation or live model run','reference_commit':'8d544b865e19c5bd286e14201af777efb694b81d','cases':summaries},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Integration results:',folder)


if __name__=='__main__':main()
