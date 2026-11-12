"""Optional PR5 simulated wiring test, not semantic/model acceptance."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import uuid
from provider_setup import create_provider
from review_handoff import make_review_packet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--team-root', required=True)
    args = parser.parse_args()
    team_root = Path(args.team_root).resolve()
    if not (team_root / 'dynamic_evidence' / 'controller.py').is_file():
        raise SystemExit('Choose the PR5 repository root containing dynamic_evidence/')
    sys.path.insert(0, str(team_root))
    from dynamic_evidence.cases import make_case
    from dynamic_evidence.controller import Harness
    from dynamic_evidence.mock_model import FixtureModel
    out = Path(__file__).resolve().parent / 'raw_outputs' / ('integration_' + uuid.uuid4().hex)
    out.mkdir(parents=True)
    report = []
    cases = [('DYN-01', 'bundle-01'), ('NO-TICKET', 'bundle-02'), ('REFERRAL', 'bundle-03'),
             ('AMOUNT', 'bundle-04'), ('LATE-TICKET', 'bundle-05'), ('BOUNDARY', 'bundle-06'),
             ('MISSING-TICKET', 'bundle-07'), ('MAINTENANCE', 'bundle-08'), ('CONFLICT', 'bundle-09'),
             ('EMPTY-CONTRACT', 'bundle-10'), ('TICKET-403', 'bundle-01'), ('CONTRACT-403', 'bundle-01'),
             ('OLD-CONTRACT', 'bundle-01')]
    for index, (name, dataset) in enumerate(cases, 1):
        original_task, original = make_case(name)
        baseline = Harness(FixtureModel(), original).run(original_task)
        # Neutral task IDs; no scenario configuration or case label in model payload.
        task = {**original_task, 'task_id': 'TASK-' + str(index).zfill(3), 'scenarios': {}}
        faults = dict(original_task.get('scenarios', {}))
        # This bundle already freezes the two original conflicting clauses.
        # No runtime answer/condition generation is needed in the provider.
        if dataset == 'bundle-09':
            faults.pop('CRM_CONTRACT_DB', None)
        p = create_provider(dataset, faults=faults, log_path=out / 'provider_calls.jsonl')
        result = Harness(FixtureModel(), p).run(task)
        actual = result['answer']['recommendation']
        expected = baseline['answer']['recommendation']
        packets = []
        if result['graph']['workflow_status'] == 'escalated':
            packet = make_review_packet(result['graph'], result['tool_receipts'], result['action_log'],
                attempted_rounds=result['usage']['rounds'], total_tool_calls=result['usage']['tool_calls'],
                questions=['请按缺口与保留原文核查，勿跳过权限和语义未决项。'])
            (out / ('review_' + str(index) + '.json')).write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding='utf-8')
            packets.append('review_' + str(index) + '.json')
        (out / ('run_' + str(index) + '.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        mismatch = None
        if actual != expected:
            # No semantic repair in the tool: expose incompatibility rather than add a gold flag.
            mismatch = 'Upstream graph currently expects maintenance.excluded; raw material returns planned. Owner must confirm semantic mapping.' if name == 'MAINTENANCE' else 'Requires owner review'
        report.append({'development_case': name, 'mode': 'simulated', 'reference': expected,
                       'actual': actual, 'same_recommendation': actual == expected,
                       'known_interface_issue': mismatch, 'review_packets': packets})
        print(name, 'reference=', expected, 'actual=', actual, 'MATCH' if actual == expected else 'REVIEW')
    summary = {'reference_pr': 5, 'reference_commit': '8d544b865e19c5bd286e14201af777efb694b81d',
               'description': 'Development simulated wiring check. No live model, no independent gold validation.',
               'cases': report}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Summary:', out / 'summary.json')


if __name__ == '__main__': main()
