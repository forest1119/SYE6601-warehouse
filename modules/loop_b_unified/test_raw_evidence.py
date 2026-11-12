import json
from pathlib import Path
import tempfile
import unittest
from copy import deepcopy
from provider_setup import create_provider
from raw_evidence import RawEvidenceTools, REGISTRY
from review_handoff import make_review_packet

TASK = {'task_id': 'T1', 'run_id': 'R1', 'customer_id': 'C-DEMO',
        'incident_id': 'I-DEMO', 'event_time': '2026-10-01T00:00:00Z'}


def read_all(provider, source, task=None):
    pages = []
    cursor = None
    for _ in range(6):
        r = provider(source, task or TASK, cursor)
        pages.append(r)
        if r['tool_status'] != 'SUCCESS' or r['pagination_complete']:
            return pages
        cursor = r['next_page_token']
    raise AssertionError('Unbounded pages')


class RawTests(unittest.TestCase):
    def test_registry_is_frozen(self):
        with self.assertRaises(TypeError):
            REGISTRY['OTHER'] = 'x'
    def test_scope_and_references(self):
        p = create_provider()
        for source in REGISTRY:
            for receipt in read_all(p, source):
                self.assertEqual(receipt['tool_status'], 'SUCCESS')
                self.assertEqual(receipt['run_id'], 'R1')
                self.assertIn('scope_declaration', receipt)
                for r in receipt['records']:
                    self.assertEqual(p.resolve_reference(r['source_id'], r['record_id'], r['locator']), r['excerpt'])
                    self.assertIn('context', r)
    def test_contract_condition_is_on_second_page(self):
        p = create_provider()
        pages = read_all(p, 'CRM_CONTRACT_DB')
        self.assertEqual(len(pages), 2)
        self.assertNotIn('24 hours', pages[0]['records'][0]['excerpt'])
        self.assertIn('24 hours', pages[1]['records'][0]['excerpt'])
        self.assertFalse(pages[0]['pagination_complete'])
    def test_contract_context_includes_adjacent_clause(self):
        p = create_provider()
        pages = read_all(p, 'CRM_CONTRACT_DB')
        self.assertNotIn('24 hours', pages[0]['records'][0]['context']['text'])
        self.assertIn('90 minutes', pages[1]['records'][0]['context']['text'])
        self.assertIn('24 hours', pages[1]['records'][0]['context']['text'])
    def test_empty_first_page_is_partial(self):
        p = create_provider(faults={'MAINTENANCE_CALENDAR': 'paged'})
        pages = read_all(p, 'MAINTENANCE_CALENDAR')
        self.assertEqual(pages[0]['records'], [])
        self.assertFalse(pages[0]['pagination_complete'])
        self.assertTrue(pages[1]['pagination_complete'])
    def test_customer_filter(self):
        r = create_provider()('CRM_CONTRACT_DB', {**TASK, 'customer_id': 'OTHER'})
        self.assertEqual(r['records'], [])
        self.assertTrue(r['pagination_complete'])
    def test_incident_filter(self):
        self.assertEqual(create_provider()('INCIDENT_DB', {**TASK, 'incident_id': 'OTHER'})['records'], [])
    def test_invalid_cursor_and_cross_run(self):
        p = create_provider()
        token = p('CRM_CONTRACT_DB', TASK)['next_page_token']
        for source, task, page in [('CRM_CONTRACT_DB', TASK, 'bad'),
                                   ('POLICY_DB', TASK, token),
                                   ('CRM_CONTRACT_DB', {**TASK, 'run_id': 'R2'}, token)]:
            r = p(source, task, page)
            self.assertEqual(r['tool_status'], 'ERROR')
            self.assertFalse(r['pagination_complete'])
    def test_paged_cursor_cannot_skip(self):
        p = create_provider(faults={'CRM_CONTRACT_DB': 'paged'})
        token = p('CRM_CONTRACT_DB', TASK)['next_page_token']
        self.assertEqual(p('CRM_CONTRACT_DB', TASK, token.rsplit(':', 1)[0] + ':2')['tool_status'], 'ERROR')
    def test_invalid_task(self):
        for update in ({'run_id': ''}, {'event_time': '2026-10-01'}):
            with self.assertRaises(ValueError):
                create_provider()('POLICY_DB', {**TASK, **update})
    def test_no_unknown_tool(self):
        with self.assertRaises(ValueError):
            create_provider()('NOT_REGISTERED', TASK)
    def test_failures_not_empty_complete(self):
        for source in REGISTRY:
            for mode, status in [('forbidden', 'FORBIDDEN'), ('timeout', 'TIMEOUT')]:
                r = create_provider(faults={source: mode})(source, TASK)
                self.assertEqual(r['tool_status'], status)
                self.assertFalse(r['pagination_complete'])
    def test_no_own_ticket_provider(self):
        r = RawEvidenceTools()('TICKET_DB', TASK)
        self.assertEqual(r['error_code'], 'TICKET_PROVIDER_NOT_CONFIGURED')
        self.assertFalse(r['pagination_complete'])
    def test_pr5_ticket_delegate_actual(self):
        p = create_provider()
        r = p('TICKET_DB', TASK)
        self.assertEqual(r['records'][0]['submitted_at'], '2026-10-01T12:00:00Z')
        self.assertEqual(r['upstream_receipt']['records'][0]['evidence_id'], 'T-01')
    def test_wrong_upstream_identity_not_trusted(self):
        p = create_provider(pr5_ticket_provider=lambda *a: {'source_type': 'TICKET_DB', 'customer_id': 'OTHER'})
        self.assertEqual(p('TICKET_DB', TASK)['tool_status'], 'ERROR')
    def test_no_answer_or_fault_label_in_receipt(self):
        forbidden = {'gold_graph', 'expected_obligations', 'expected_supports', 'final_decision',
                     'scenario', 'bundle_id', 'source_case', 'expected_decision'}
        def walk(obj):
            if isinstance(obj, dict):
                self.assertFalse(forbidden.intersection(obj))
                for v in obj.values(): walk(v)
            elif isinstance(obj, list):
                for v in obj: walk(v)
        p = create_provider()
        for source in REGISTRY:
            for r in read_all(p, source, {**TASK, 'scenarios': {'TICKET_DB': 'forbidden'}, 'expected_decision': True}):
                walk(r)
    def test_no_ticket_condition_in_other_contract(self):
        pages = read_all(create_provider('bundle-02'), 'CRM_CONTRACT_DB')
        self.assertNotIn('24 hours', str([r['excerpt'] for p in pages for r in p['records']]))
    def test_referral_and_unavailable_context(self):
        rows = [r for p in read_all(create_provider('bundle-03'), 'CRM_CONTRACT_DB') for r in p['records']]
        self.assertTrue(any('Schedule Z' in r['excerpt'] for r in rows))
        r = create_provider('bundle-11')('CRM_CONTRACT_DB', TASK)['records'][0]
        self.assertIsNone(r['context']['text'])
        self.assertFalse(r['context']['available'])
    def test_override_raw_thresholds_not_support_labels(self):
        p = create_provider()
        policy = p('POLICY_DB', TASK)['records'][0]['excerpt']
        contract = p('CRM_CONTRACT_DB', TASK)['records'][0]['excerpt']
        self.assertIn('60 minutes', policy)
        self.assertIn('90 minutes', contract)
        self.assertNotIn('overrides', p.receipts[-1])
    def test_no_fabricated_amount(self):
        p = create_provider('bundle-04')
        self.assertNotIn('$500', str([read_all(p, source) for source in REGISTRY]))
    def test_old_material_still_success(self):
        r = create_provider(faults={'CRM_CONTRACT_DB': 'old_version'})('CRM_CONTRACT_DB', TASK)
        self.assertEqual(r['tool_status'], 'SUCCESS')
        self.assertEqual(r['records'][0]['effective_to'], '2024-12-31T23:59:59Z')
    def test_replay_materials_with_fixed_clock_and_call_id(self):
        r = []
        for _ in range(2):
            a = create_provider(fetched_at='2026-11-12T00:00:00Z').query('POLICY_DB', TASK, call_id='CALL1')
            a.pop('elapsed'); a.pop('elapsed_ms'); r.append(a)
        self.assertEqual(r[0], r[1])
    def test_unique_calls_and_return_copy(self):
        p = create_provider()
        a = p.query('POLICY_DB', TASK, call_id='CALL1')
        a['records'].clear()
        self.assertTrue(p.receipts[0]['records'])
        with self.assertRaises(ValueError): p.query('POLICY_DB', TASK, call_id='CALL1')
    def test_log_append(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'calls.jsonl'
            p = create_provider(log_path=path)
            p('POLICY_DB', TASK); p('INCIDENT_DB', TASK)
            self.assertEqual(len(path.read_text(encoding='utf-8').splitlines()), 2)
    def test_log_failure_propagates(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(OSError): create_provider(log_path=d)('POLICY_DB', TASK)
    def test_bad_reference_rejected(self):
        p = create_provider(); r = p('POLICY_DB', TASK)['records'][0]
        with self.assertRaises(ValueError): p.resolve_reference(r['source_id'], r['record_id'], {'unit': 'unicode_code_points', 'start': 0, 'end': 1})


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.p = create_provider(faults={'TICKET_DB': 'forbidden'})
        read_all(self.p, 'CRM_CONTRACT_DB'); self.p('TICKET_DB', TASK)
        self.snapshot = {'task_id': 'T1', 'run_id': 'R1', 'graph_version': 3, 'answer_version': 2,
                         'recommendation': 'undetermined', 'workflow_status': 'escalated', 'stop_reason': 'ACCESS_DENIED',
                         'gaps': [{'affected_claim_ids': ['C1'], 'reason': 'ticket denied'}]}
    def packet(self, receipts=None, snapshot=None, **extra):
        return make_review_packet(snapshot or self.snapshot, self.p.receipts if receipts is None else receipts,
                                  [], attempted_rounds=1, questions=['Check ticket permission'], **extra)
    def test_packet_preserves_new_clause_when_ticket_denied(self):
        p = self.packet()
        self.assertTrue(any('24 hours' in r['excerpt'] for r in p['original_materials']))
        self.assertEqual(p['failed_tools'][0]['source_type'], 'TICKET_DB')
        self.assertEqual(p['graph_version'], 3)
        self.assertEqual(p['answer_version'], 2)
        self.assertEqual(p['attempted_rounds'], 1)
        self.assertEqual(p['total_tool_calls'], 3)
    def test_cross_run_and_duplicate_calls_rejected(self):
        a = self.p.receipts; a[0]['run_id'] = 'OTHER'
        with self.assertRaises(ValueError): self.packet(receipts=a)
        with self.assertRaises(ValueError): self.packet(receipts=self.p.receipts * 2)
    def test_snapshot_must_be_terminal(self):
        with self.assertRaises(ValueError): self.packet(snapshot={**self.snapshot, 'workflow_status': 'checking'})
    def test_count_not_smaller_than_receipts(self):
        with self.assertRaises(ValueError): self.packet(total_tool_calls=1)
    def test_does_not_mutate_snapshot(self):
        old = deepcopy(self.snapshot); packet = self.packet(); packet['unresolved_gaps'].clear()
        self.assertEqual(self.snapshot, old)


if __name__ == '__main__': unittest.main(verbosity=2)
