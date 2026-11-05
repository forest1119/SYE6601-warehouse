"""使用固定分支的真实模拟函数进行联调测试，不修改同学源码。"""
from copy import deepcopy
from pathlib import Path
import unittest
from checker_api import read_json,make_score_snapshot
from checker_v2 import InputError
from loop_b_adapter import adapt_loop_b,merge_loop_b_pages
from run_loop_b_integration import sample_task,contract_call,maintenance_call,integration_cases
from confidence_a import score_snapshot
RULES=read_json(Path(__file__).parent/'rules.json')

class LoopBTests(unittest.TestCase):
    def test_all_eight_actual_tool_cases(self):
        count=0
        for name,task,calls in integration_cases():
            with self.subTest(name=name):
                before=deepcopy(calls)
                result=adapt_loop_b(task,calls,RULES)
                self.assertEqual(calls,before)
                self.assertEqual(result,adapt_loop_b(task,calls,RULES))
                self.assertIsNone(result['checker_result']['current_decision'])
                card=score_snapshot(make_score_snapshot(result['checker_result'],'RUN','SNAP'))
                self.assertFalse(card['may_present_definitive_decision'])
                count+=1
        self.assertEqual(count,8)

    def test_missing_scope_and_clauses_not_fabricated(self):
        result=adapt_loop_b(sample_task(),{'CRM_CONTRACT_DB':[contract_call('002')]},RULES)
        r=result['normalized_responses']['CRM_CONTRACT_DB']['records'][0]
        self.assertIsNone(r['scope']);self.assertNotIn('terms',r);self.assertNotIn('rule_id',r)
        self.assertEqual(r['original_scope'],{'customer_id':'002'})
        self.assertEqual({g['field'] for g in result['adapter_gaps']},{'scope/service_scope','rule_id','terms'})

    def test_forbidden_mapping_and_timeout(self):
        for scenario,status in [('forbidden','ACCESS_DENIED'),('timeout','TIMEOUT')]:
            result=adapt_loop_b(sample_task(),{'CRM_CONTRACT_DB':[contract_call('002',scenario)]},RULES)
            r=result['normalized_responses']['CRM_CONTRACT_DB']
            self.assertEqual(r['tool_status'],status);self.assertFalse(r['pagination_complete'])
            self.assertEqual(result['raw_tool_calls']['CRM_CONTRACT_DB'][0]['response']['tool_status'],
                             'FORBIDDEN' if scenario=='forbidden' else 'TIMEOUT')

    def test_empty_first_page_not_absence(self):
        receipt,issues,_=merge_loop_b_pages(sample_task(),'MAINTENANCE_CALENDAR',[maintenance_call('002')])
        self.assertFalse(receipt['pagination_complete']);self.assertEqual(receipt['records'],[])

    def test_two_pages_merge_and_rename(self):
        result=adapt_loop_b(sample_task(),{'MAINTENANCE_CALENDAR':[maintenance_call('002'),maintenance_call('002','page_2')]},RULES)
        r=result['normalized_responses']['MAINTENANCE_CALENDAR']
        self.assertTrue(r['pagination_complete']);self.assertEqual(len(r['records']),1)
        record=r['records'][0]
        self.assertEqual(record['start'],record['maintenance_start'])
        self.assertNotIn('planned',record)
        self.assertIn('MISSING_PLANNED_FLAG',[g['code'] for g in result['adapter_gaps']])

    def test_page_two_alone_not_complete(self):
        r,issues,_=merge_loop_b_pages(sample_task(),'MAINTENANCE_CALENDAR',[maintenance_call('002','page_2')])
        self.assertFalse(r['pagination_complete']);self.assertIn('BROKEN_PAGE_CHAIN',issues)

    def test_wrong_customer_does_not_pass(self):
        r,issues,_=merge_loop_b_pages(sample_task(),'CRM_CONTRACT_DB',[contract_call('001')])
        self.assertFalse(r['pagination_complete']);self.assertIn('WRONG_CUSTOMER_QUERY',issues)

    def test_old_version_uses_dates(self):
        result=adapt_loop_b(sample_task(),{'CRM_CONTRACT_DB':[contract_call('002','old_version')]},RULES)
        self.assertFalse(result['metadata_observations'][0]['time_valid_at_incident'])
        self.assertEqual(result['metadata_observations'][0]['version_label'],'v0')

    def test_opposite_text_is_not_business_conflict(self):
        result=adapt_loop_b(sample_task(),{'CRM_CONTRACT_DB':[contract_call('002','conflicting_materials')]},RULES)
        self.assertEqual(result['checker_result']['obligation_results'][0]['status'],'UNKNOWN')
        self.assertIn('UNSTRUCTURED_STATEMENT_NOT_JUDGED',[g['code'] for g in result['adapter_gaps']])

    def test_mixed_scenarios_and_duplicate_pages_rejected(self):
        calls=[maintenance_call('002'),maintenance_call('002','page_2','old_version')]
        r,issues,_=merge_loop_b_pages(sample_task(),'MAINTENANCE_CALENDAR',calls)
        self.assertIn('MIXED_PAGE_SCENARIOS',issues);self.assertFalse(r['pagination_complete'])
        calls=[maintenance_call('002'),maintenance_call('002','page_2'),maintenance_call('002','page_2')]
        with self.assertRaises(InputError):merge_loop_b_pages(sample_task(),'MAINTENANCE_CALENDAR',calls)

    def test_page_end_with_token_not_complete(self):
        calls=[maintenance_call('002'),maintenance_call('002','page_2')]
        calls[-1]['response']['next_page_token']='page_3'
        r,issues,_=merge_loop_b_pages(sample_task(),'MAINTENANCE_CALENDAR',calls)
        self.assertFalse(r['pagination_complete']);self.assertIn('CONTRADICTORY_PAGE_END',issues)

if __name__=='__main__':unittest.main()
