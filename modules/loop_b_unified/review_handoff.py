"""Format Loop A's terminal snapshot. No new business/graph decisions."""
from copy import deepcopy
from pathlib import Path
import json
import uuid


def make_review_packet(snapshot, receipts, action_log, *, attempted_rounds,
                       questions, total_tool_calls=None):
    if not isinstance(snapshot, dict):
        raise ValueError('snapshot must be an object supplied by Loop A')
    fields = ('task_id', 'run_id', 'graph_version', 'answer_version',
              'recommendation', 'workflow_status', 'stop_reason')
    for field in fields:
        if field not in snapshot:
            raise ValueError('Missing terminal field: ' + field)
    for field in ('task_id', 'run_id', 'stop_reason'):
        if not isinstance(snapshot[field], str) or not snapshot[field].strip():
            raise ValueError('Invalid ' + field)
    for field in ('graph_version', 'answer_version'):
        if type(snapshot[field]) is not int or snapshot[field] < 0:
            raise ValueError('Invalid ' + field)
    if snapshot['recommendation'] not in ('eligible', 'ineligible', 'undetermined'):
        raise ValueError('Unknown recommendation')
    if snapshot['workflow_status'] not in ('checking', 'needs_clarification', 'escalated', 'completed'):
        raise ValueError('Unknown workflow_status')
    if snapshot['workflow_status'] == 'checking':
        raise ValueError('Loop A must supply a stopped/clarification snapshot')
    if type(attempted_rounds) is not int or attempted_rounds < 0:
        raise ValueError('Round count must come from Loop A')
    if not isinstance(questions, list) or not questions or any(not isinstance(q, str) or not q.strip() for q in questions):
        raise ValueError('Human verification questions required')
    if not isinstance(receipts, list) or not isinstance(action_log, list):
        raise ValueError('receipts/action_log must be lists')
    gaps = snapshot.get('gaps')
    if not isinstance(gaps, list) or any(not isinstance(g, dict) for g in gaps):
        raise ValueError('Snapshot gaps must be an explicit list')
    seen = set()
    originals, failed, sources = [], [], []
    for receipt in receipts:
        if not isinstance(receipt, dict) or any(receipt.get(k) != snapshot[k] for k in ('task_id', 'run_id')):
            raise ValueError('Cross-task/run receipt rejected')
        cid = receipt.get('call_id')
        if not isinstance(cid, str) or not cid or cid in seen:
            raise ValueError('Missing or duplicate call_id')
        seen.add(cid)
        status = receipt.get('tool_status')
        if status not in ('SUCCESS', 'FORBIDDEN', 'TIMEOUT', 'ERROR'):
            raise ValueError('Invalid tool status')
        if not isinstance(receipt.get('source_type'), str):
            raise ValueError('Missing queried source')
        if receipt['source_type'] not in sources:
            sources.append(receipt['source_type'])
        if status != 'SUCCESS':
            failed.append({'call_id': cid, 'source_type': receipt['source_type'],
                           'tool_status': status, 'error_code': receipt.get('error_code')})
        records = receipt.get('records')
        if not isinstance(records, list):
            raise ValueError('Receipt records must be a list')
        for row in records:
            if not isinstance(row, dict):
                raise ValueError('Malformed original material')
            originals.append({'call_id': cid, 'provider_call_id': receipt.get('provider_call_id', cid),
                              **{k: deepcopy(row.get(k)) for k in ('source_id', 'record_id', 'locator', 'excerpt',
                                       'context', 'citation', 'customer_id', 'incident_id', 'version')},
                              'raw_record': deepcopy(row)})
    if total_tool_calls is None:
        total_tool_calls = len(receipts)
    if type(total_tool_calls) is not int or total_tool_calls < len(receipts):
        raise ValueError('Total calls cannot be smaller than supplied receipts')
    affected = []
    for gap in gaps:
        ids = gap.get('affected_claim_ids', [])
        if not isinstance(ids, list):
            raise ValueError('affected_claim_ids must be a list')
        for item in ids:
            if item not in affected:
                affected.append(item)
    packet = {'schema_version': 'loop-b-review-0.2-draft',
              **{k: deepcopy(snapshot[k]) for k in fields},
              'requested_by': 'LOOP_A', 'queried_sources': sources,
              'affected_claim_ids': affected, 'unresolved_gaps': deepcopy(gaps),
              'original_materials': originals, 'failed_tools': failed,
              'attempted_rounds': attempted_rounds, 'total_tool_calls': total_tool_calls,
              'provided_receipts_count': len(receipts), 'action_log': deepcopy(action_log),
              'questions_for_human': list(questions), 'tool_receipts': deepcopy(receipts),
              'scope_declaration': deepcopy(snapshot.get('scope_declaration'))}
    json.dumps(packet, ensure_ascii=False, allow_nan=False)
    return packet


def save_review_packet(packet, folder):
    encoded = json.dumps(packet, ensure_ascii=False, indent=2, allow_nan=False)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ('review_' + uuid.uuid4().hex + '.json')
    with path.open('x', encoding='utf-8') as stream:
        stream.write(encoded)
    return path
