"""开发回归测试与07A实际接口联调：运行 python -m unittest -v。"""
import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import test_checker_v2 as previous
from checker_api import check_payload,make_score_snapshot,read_json
from checker_v2 import InputError
sys.path.insert(0,str(Path(__file__).parent/'vendor'))
from confidence_a import score_snapshot, ContractError

ROOT=Path(__file__).resolve().parent
RULES=json.loads((ROOT/'rules.json').read_text(encoding='utf-8'))

class HandoffTests(unittest.TestCase):
    def fixture(self):
        task,responses=previous.make_fixture()
        return {'task':task,'responses':responses,'rules':deepcopy(RULES)}

    def test_all_business_cases_and_scoring(self):
        # 用前一版的独立场景函数检查新入口，同时实测评分组原始代码。
        original=previous.run_checker_v2
        collected={}
        def adapted(task,responses,rules):
            result=check_payload({'task':task,'responses':responses,'rules':rules})
            collected[result['snapshot_fingerprint']]=result
            return result
        previous.run_checker_v2=adapted
        try:
            rows=previous.run_checks(RULES)
        finally:
            previous.run_checker_v2=original
        self.assertEqual(len(rows),51)
        for result in collected.values():
            with self.subTest(result=result['snapshot_fingerprint']):
                snapshot=make_score_snapshot(result,'TEST-RUN','TEST-SNAPSHOT')
                card=score_snapshot(snapshot)
                self.assertEqual(card['checker_decision'],result['checker_decision'])
                self.assertEqual(card['may_present_definitive_decision'],result['current_decision'] is not None)
                self.assertEqual(len(snapshot['obligations']),6)
        self.assertEqual(len(collected),49)

    def test_input_is_not_mutated(self):
        payload=self.fixture();before=deepcopy(payload)
        check_payload(payload)
        self.assertEqual(payload,before)

    def test_dependency_gaps(self):
        payload=self.fixture();payload['responses'].pop('CRM_CONTRACT_DB')
        result=check_payload(payload)
        gaps={g['obligation_id']:g for g in result['gaps']}
        self.assertTrue(gaps['B-CONTRACT']['ready_for_lookup'])
        self.assertFalse(gaps['B-DURATION']['ready_for_lookup'])
        self.assertEqual(gaps['B-DURATION']['blocked_by'],['B-CONTRACT'])

    def test_single_bad_incident_is_unknown_not_conflict(self):
        payload=self.fixture()
        payload['responses']['MONITORING_SYSTEM']['records'][0]['incident_id']='INC-WRONG'
        result=check_payload(payload)
        ob=next(o for o in result['obligation_results'] if o['obligation_id']=='B-DURATION')
        self.assertEqual(ob['status'],'UNKNOWN')

    def test_blank_contract_identity_cannot_fallback(self):
        payload=self.fixture();payload['responses']['CRM_CONTRACT_DB']['records'][0]['customer_id']=''
        result=check_payload(payload)
        self.assertIsNone(result['current_decision'])
        self.assertIsNone(result['selected_rule_id'])

    def test_reserved_reference_rejected(self):
        payload=self.fixture();payload['responses']['PLAN_DB']['records'][0]['evidence_id']='POLICY:RULE-001'
        with self.assertRaises(InputError):check_payload(payload)

    def test_nonfinite_and_nonjson_rejected(self):
        for invalid in [float('nan'),float('inf'),object()]:
            payload=self.fixture();payload['task']['unexpected']=invalid
            with self.assertRaises(InputError):check_payload(payload)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'bad.json';p.write_text('{"a":1,"a":2}')
            with self.assertRaises(InputError):read_json(p)

    def test_escalation_requires_actual_flow_input(self):
        payload=self.fixture();payload['responses']['CRM_CONTRACT_DB']['tool_status']='ACCESS_DENIED'
        result=check_payload(payload)
        snap=make_score_snapshot(result,'RUN','SNAP')
        self.assertEqual(snap['process_state'],'RUNNING')
        with self.assertRaises(InputError):make_score_snapshot(result,'RUN','SNAP','ESCALATED')
        snap=make_score_snapshot(result,'RUN','SNAP','ESCALATED','Loop演示确认已转人工')
        self.assertFalse(score_snapshot(snap)['may_present_definitive_decision'])
        with self.assertRaises(InputError):make_score_snapshot(check_payload(self.fixture()),'RUN','SNAP','ESCALATED','已升级')

    def test_skipped_obligations_not_deleted(self):
        p=self.fixture();p['responses']['CRM_CONTRACT_DB']['records'][0]['terms']['allows_compensation']=False
        result=check_payload(p);snap=make_score_snapshot(result,'RUN','SNAP');card=score_snapshot(snap)
        self.assertEqual(len(snap['obligations']),6)
        self.assertEqual(card['denominator_count'],6)
        self.assertTrue(card['gate_passed'])
        self.assertLess(card['score'],100)

    def test_cli_end_to_end_and_error_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);inp=p/'input.json';out=p/'output.json';snap=p/'snapshot.json'
            inp.write_text(json.dumps(self.fixture()),encoding='utf-8')
            cmd=[sys.executable,str(ROOT/'run_checker.py'),str(inp),'--output',str(out),'--score-snapshot',str(snap)]
            run=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertTrue(json.loads(out.read_text())['current_decision'])
            score_snapshot(json.loads(snap.read_text()))
            inp.write_text('{"bad":')
            failed=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(failed.returncode,2)
            self.assertIn('错误',failed.stderr)
            self.assertEqual(json.loads(out.read_text())['status'],'INPUT_ERROR')
            self.assertNotIn('checker_decision',json.loads(snap.read_text()))
            self.assertEqual(subprocess.run([sys.executable,str(ROOT/'run_checker.py'),str(inp),'--output',str(inp)],capture_output=True).returncode,2)

if __name__=='__main__':unittest.main()
