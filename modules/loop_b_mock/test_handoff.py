import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from loop_b_handoff import call_with_log, make_escalation, save_escalation
from mock_tools import get_customer_contract

class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.log=self.folder/'calls.jsonl'
    def call(self, tool='get_customer_contract', **params):
        return call_with_log('T1',tool,params or {'customer_id':'002'},self.log)
    def sheet(self,entries,task='T1',rounds=1):
        return make_escalation(task,'002','Loop A requested review',['contract'],[],entries,rounds,['Please verify contract'])
    def test_response_unchanged(self):
        r=self.call()['response']; expected=get_customer_contract('002')
        r.pop('fetched_at');expected.pop('fetched_at')
        self.assertEqual(r,expected)
    def test_log_appends_and_unique_ids(self):
        a=self.call();b=self.call()
        rows=[json.loads(s) for s in self.log.read_text(encoding='utf-8').splitlines()]
        self.assertEqual(len(rows),2)
        self.assertNotEqual(rows[0]['call_id'],rows[1]['call_id'])
        self.assertEqual(rows[0]['parameters'],{'customer_id':'002'})
        self.assertGreaterEqual(rows[0]['elapsed_ms'],0)
    def test_page_logged_no_auto_followup(self):
        r=self.call('list_maintenance',customer_id='002')
        self.assertEqual(r['response']['next_page_token'],'page_2')
        self.assertFalse(r['response']['pagination_complete'])
        self.assertEqual(len(self.log.read_text(encoding='utf-8').splitlines()),1)
    def test_errors_preserved_no_auto_escalation(self):
        for scenario,status in [('forbidden','FORBIDDEN'),('timeout','TIMEOUT')]:
            r=self.call(customer_id='002',scenario=scenario)
            self.assertEqual(r['log_entry']['tool_status'],status)
        self.assertEqual(list(self.folder.glob('escalation*')),[])
    def test_tool_exception_logged(self):
        with patch('loop_b_handoff.TOOLS',{'broken':lambda:1/0}):
            r=call_with_log('T1','broken',{},self.log)
        self.assertEqual(r['response']['tool_status'],'ERROR')
        self.assertEqual(r['log_entry']['exception']['type'],'ZeroDivisionError')
    def test_unknown_tool_rejected(self):
        with self.assertRaises(ValueError):self.call('not_registered')
        self.assertFalse(self.log.exists())
    def test_log_failure_propagates(self):
        with self.assertRaises(OSError):call_with_log('T1','get_customer_contract',{'customer_id':'002'},self.folder)
    def test_no_implicit_round_count(self):
        entries=[self.call()['log_entry'] for _ in range(3)]
        self.assertEqual(self.sheet(entries,rounds=2)['attempted_rounds'],2)
    def test_failed_tools_and_copy(self):
        entry=self.call(customer_id='002',scenario='forbidden')['log_entry']
        doc=self.sheet([entry]);entry['tool']='changed'
        self.assertEqual(doc['failed_tools'][0]['tool'],'get_customer_contract')
        self.assertEqual(doc['evidence_ids'],[])
        self.assertEqual(doc['attempted_actions'][0]['tool'],'get_customer_contract')
    def test_mixed_tasks_rejected(self):
        with self.assertRaises(ValueError):self.sheet([self.call()['log_entry']],task='OTHER')
    def test_no_overwrite_on_save(self):
        doc=self.sheet([]);a=save_escalation(doc,self.folder);b=save_escalation(doc,self.folder)
        self.assertNotEqual(a,b)
        self.assertEqual(json.loads(a.read_text(encoding='utf-8')),doc)
    def test_invalid_inputs(self):
        for cost in [-1,float('nan'),True]:
            with self.assertRaises(ValueError):call_with_log('T1','get_customer_contract',{},self.log,cost)
        with self.assertRaises(ValueError):self.sheet([],rounds=True)

if __name__=='__main__':unittest.main(verbosity=2)
