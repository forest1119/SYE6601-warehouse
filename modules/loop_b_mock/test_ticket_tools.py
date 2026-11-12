import json
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ticket_tools import get_ticket, extension_query
from loop_b_handoff import call_with_log

class TicketTests(unittest.TestCase):
    def test_submission_timestamp_is_raw_evidence(self):
        r=get_ticket('C-DEMO','I-DEMO')
        self.assertEqual(r['tool_status'],'SUCCESS')
        self.assertEqual(len(r['records']),1)
        row=r['records'][0]
        self.assertEqual(row['submitted_at'],'2026-10-01T12:00:00Z')
        self.assertIsNotNone(datetime.fromisoformat(row['submitted_at'].replace('Z','+00:00')).utcoffset())
        self.assertNotEqual(row['submitted_at'],r['fetched_at'])
        self.assertNotIn('eligible',r)
        self.assertNotIn('final_decision',r)
    def test_filter_customer(self):
        r=get_ticket('OTHER','I-DEMO')
        self.assertEqual(r['records'],[])
        self.assertTrue(r['pagination_complete'])
    def test_filter_incident(self):
        self.assertEqual(get_ticket('C-DEMO','OTHER')['records'],[])
    def test_identity_required(self):
        for cid,iid in [('', 'I-DEMO'),('C-DEMO',None),(' ', 'I-DEMO')]:
            r=get_ticket(cid,iid)
            self.assertEqual(r['tool_status'],'ERROR')
            self.assertFalse(r['pagination_complete'])
    def test_forbidden(self):
        r=get_ticket('C-DEMO','I-DEMO','forbidden')
        self.assertEqual(r['tool_status'],'FORBIDDEN')
        self.assertEqual(r['error_code'],403)
        self.assertFalse(r['pagination_complete'])
    def test_timeout(self):
        r=get_ticket('C-DEMO','I-DEMO','timeout')
        self.assertEqual(r['tool_status'],'TIMEOUT')
        self.assertFalse(r['pagination_complete'])
    def test_missing_complete(self):
        r=get_ticket('C-DEMO','I-DEMO','missing_ticket')
        self.assertEqual(r['records'],[])
        self.assertTrue(r['pagination_complete'])
    def test_late_and_boundary_are_returned_not_judged(self):
        for scenario,date in [('late_ticket','2026-10-02T00:00:01Z'),('boundary','2026-10-02T00:00:00Z')]:
            r=get_ticket('C-DEMO','I-DEMO',scenario)
            self.assertEqual(r['records'][0]['submitted_at'],date)
            self.assertEqual(r['tool_status'],'SUCCESS')
            self.assertNotIn('deadline_met',r)
    def test_paged(self):
        a=get_ticket('C-DEMO','I-DEMO','paged');b=get_ticket('C-DEMO','I-DEMO','paged','page_2')
        self.assertEqual(a['records'],[])
        self.assertFalse(a['pagination_complete'])
        self.assertEqual(a['next_page_token'],'page_2')
        self.assertTrue(b['pagination_complete'])
        self.assertIsNone(b['next_page_token'])
        self.assertEqual(len(b['records']),1)
    def test_bad_pages(self):
        for scenario,page in [('normal','page_2'),('paged','unknown'),('paged',[])]:
            self.assertEqual(get_ticket('C-DEMO','I-DEMO',scenario,page)['tool_status'],'ERROR')
    def test_bad_scenarios(self):
        for s in ['unknown',[],None]:
            self.assertEqual(get_ticket('C-DEMO','I-DEMO',s)['tool_status'],'ERROR')
    def test_old_version_does_not_mutate_source(self):
        r=get_ticket('C-DEMO','I-DEMO','old_version')
        self.assertEqual(r['records'][0]['effective_to'],'2024-12-31T23:59:59Z')
        self.assertEqual(get_ticket('C-DEMO','I-DEMO')['records'][0]['version'],'v1')
    def test_missing_file_is_error_not_absence(self):
        with tempfile.TemporaryDirectory() as d, patch('ticket_tools.DATA_PATH',Path(d)/'missing.json'):
            r=get_ticket('C-DEMO','I-DEMO')
            self.assertEqual(r['tool_status'],'ERROR')
            self.assertFalse(r['pagination_complete'])
    def test_bad_data_is_error_not_absence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json'
            for value in ['not JSON','{}','{"fixtures":{"normal":[{}]}}']:
                p.write_text(value,encoding='utf-8')
                with patch('ticket_tools.DATA_PATH',p):
                    self.assertEqual(get_ticket('C-DEMO','I-DEMO')['tool_status'],'ERROR')
    def test_repeat_stable_except_fetch_time(self):
        a=get_ticket('C-DEMO','I-DEMO');b=get_ticket('C-DEMO','I-DEMO')
        a.pop('fetched_at');b.pop('fetched_at')
        self.assertEqual(a,b)
    def test_extension(self):
        t={'customer_id':'C-DEMO','incident_id':'I-DEMO','scenarios':{'TICKET_DB':'forbidden'}}
        self.assertEqual(extension_query('TICKET_DB',t)['tool_status'],'FORBIDDEN')
    def test_extension_unknown_source_explicit(self):
        with self.assertRaises(ValueError):extension_query('POLICY_DB',{})
    def test_logged_ticket(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'calls.jsonl'
            r=call_with_log('T1','get_ticket',{'customer_id':'C-DEMO','incident_id':'I-DEMO'},p)
            row=json.loads(p.read_text(encoding='utf-8'))
            self.assertEqual(row['parameters']['incident_id'],'I-DEMO')
            self.assertEqual(row['response'],r['response'])

if __name__=='__main__':unittest.main(verbosity=2)
