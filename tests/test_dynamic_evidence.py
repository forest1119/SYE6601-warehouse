import copy
import json
import unittest
from pathlib import Path

from dynamic_evidence.cases import make_case
from dynamic_evidence.controller import Budget, Harness
from dynamic_evidence.evaluate import GOLD, assess
from dynamic_evidence.mock_model import FixtureModel
from dynamic_evidence.models import Replay
from dynamic_evidence.report import IDENTITY, markdown
from dynamic_evidence.tools import CONTRACT, MAINTENANCE, TICKET, LoopBAdapter
from dynamic_evidence.unified import run_unified
from loop_b_unified import create_provider


def run(case="DYN-01", model=None, budget=None, strategy="dynamic"):
    task, tool = make_case(case)
    return Harness(model or FixtureModel(), tool, budget=budget).run(task, strategy=strategy)


class HarnessTests(unittest.TestCase):
    def test_unified_contract_pagination_and_reference(self):
        result = run_unified(FixtureModel())
        self.assertEqual(result["answer"]["recommendation"], "eligible")
        pages = [r for r in result["tool_receipts"] if r["source_type"] == CONTRACT]
        self.assertEqual([r["pagination_complete"] for r in pages], [False, True])
        ref = next(e for e in result["scorecard"]["evidence"] if "24 hours" in e["excerpt"])
        original = next(r for r in pages if r["call_id"] == ref["call_id"])
        self.assertEqual(original["records"][0]["locator"], ref["locator"])
        self.assertEqual(original["records"][0]["source_id"], ref["source_id"])
        self.assertTrue(original["provider_call_id"])

    def test_unified_403_builds_team_review_packet(self):
        result = run_unified(FixtureModel(), ticket_forbidden=True)
        self.assertEqual(result["graph"]["stop_reason"], "ACCESS_DENIED")
        packet = result["review_packet"]
        self.assertEqual(packet["total_tool_calls"], result["usage"]["tool_calls"])
        self.assertEqual(packet["failed_tools"][0]["source_type"], TICKET)
        self.assertTrue(any("24 hours" in (row["excerpt"] or "") for row in packet["original_materials"]))

    def test_planned_maintenance_does_not_prove_exclusion(self):
        task, _ = make_case()
        result = Harness(FixtureModel(), create_provider("bundle-08")).run(task)
        self.assertEqual(result["answer"]["recommendation"], "undetermined")
        condition = next(n for n in result["graph"]["nodes"] if n["id"] == "condition:no-maintenance-exclusion")
        self.assertEqual(condition["state"], "UNKNOWN")

    def test_dynamic_contract_expansion_and_reference_chain(self):
        result = run()
        self.assertTrue(assess(result)["dynamic_path"])
        self.assertEqual([action["source"] for action in result["action_log"]][-2:], [CONTRACT, TICKET])
        contract_snapshot = result["history"][1]
        ticket = next(n for n in contract_snapshot["nodes"] if n["id"] == "condition:ticket_deadline_hours")
        self.assertEqual((ticket["value"], ticket["state"]), (24, "UNKNOWN"))
        self.assertTrue(any(edge["type"] == "overrides" for edge in contract_snapshot["edges"]))
        for snapshot in result["history"]:
            ids = {node["id"] for node in snapshot["nodes"]}
            self.assertTrue(all(edge["from"] in ids and edge["to"] in ids for edge in snapshot["edges"]))
        self.assertIn("24 hours", markdown(result))

    def test_every_frozen_case_dynamic(self):
        for case in GOLD:
            with self.subTest(case=case):
                assessment = assess(run(case))
                self.assertTrue(assessment["terminal_correct"])
                self.assertEqual(assessment["wrong_accepted_relations"], 0)

    def test_no_ticket_clause_does_not_query_ticket(self):
        self.assertFalse(any(r["source_type"] == TICKET for r in run("NO-TICKET")["tool_receipts"]))
        self.assertTrue(any(r["source_type"] == TICKET for r in run("NO-TICKET", strategy="fixed")["tool_receipts"]))

    def test_second_page_matters_in_both_methods(self):
        for strategy in ("dynamic", "fixed"):
            result = run("MAINTENANCE", strategy=strategy)
            pages = [r for r in result["tool_receipts"] if r["source_type"] == MAINTENANCE]
            self.assertEqual([r["pagination_complete"] for r in pages], [False, True])
            self.assertEqual(result["answer"]["recommendation"], "ineligible")

    def test_contract_second_page_drives_ticket(self):
        task, tool = make_case()
        task["scenarios"][CONTRACT] = "paged"
        result = Harness(FixtureModel(), tool).run(task)
        contract = [r for r in result["tool_receipts"] if r["source_type"] == CONTRACT]
        self.assertEqual([len(r["records"]) for r in contract], [0, 2])
        self.assertTrue(assess(result)["dynamic_path"])

    def test_budget_keeps_scorecard_and_last_graph(self):
        result = run(budget=Budget(max_rounds=1))
        self.assertEqual(result["graph"]["stop_reason"], "ROUND_LIMIT")
        self.assertEqual(result["answer"]["recommendation"], "undetermined")
        self.assertEqual(result["scorecard"]["level"], "证据不足")
        self.assertIn("condition:ticket_deadline_hours", {n["id"] for n in result["graph"]["nodes"]})

    def test_permission_retains_contract_and_escalation(self):
        result = run("TICKET-403")
        self.assertEqual(result["graph"]["stop_reason"], "ACCESS_DENIED")
        self.assertEqual(result["escalation"]["workflow_status"], "escalated")
        self.assertTrue(any(e["record_id"] == "C-DEADLINE" for e in result["escalation"]["evidence"]))

    def test_model_wrong_unit_or_fabricated_excerpt_is_rejected(self):
        for fabricated in (False, True):
            class WrongModel(FixtureModel):
                def __call__(self, stage, messages, timeout):
                    reply = super().__call__(stage, messages, timeout)
                    if stage == "build":
                        body = json.loads(reply["raw_output"])
                        for condition in body["conditions"]:
                            if condition["kind"] == "ticket_deadline_hours":
                                condition["kind"] = "duration_min"
                                if fabricated:
                                    condition["excerpt"] = "At least 24 minutes."
                        reply["raw_output"] = json.dumps(body)
                    return reply
            result = run(model=WrongModel())
            self.assertEqual(result["answer"]["recommendation"], "undetermined")
            self.assertTrue(any(c["review_status"] == "rejected" for c in result["graph"]["checks"]))

    def test_malformed_build_retries_once_and_preserves_original_output(self):
        class OneInvalid(FixtureModel):
            def __init__(self):
                self.first = True

            def __call__(self, stage, messages, timeout):
                result = super().__call__(stage, messages, timeout)
                if self.first:
                    self.first = False
                    result["raw_output"] = '{"": ""}'
                return result

        result = run(model=OneInvalid())
        self.assertTrue(assess(result)["dynamic_path"])
        self.assertEqual(result["model_calls"][0]["response"]["raw_output"], '{"": ""}')
        self.assertEqual(result["model_calls"][1]["stage"], "build")
        blocked = run(model=OneInvalid(), budget=Budget(max_model_calls=1))
        self.assertEqual(blocked["graph"]["stop_reason"], "MODEL_CALL_LIMIT")

    def test_receipt_metadata_only_does_not_pass_contract_coverage(self):
        task, tool = make_case()
        for row in tool.records[CONTRACT]:
            del row["statement"]
        result = Harness(FixtureModel(), tool).run(task)
        self.assertEqual(result["answer"]["recommendation"], "undetermined")
        self.assertFalse(next(c["completed"] for c in result["graph"]["coverage"] if c["source"] == CONTRACT))

    def test_candidate_amount_is_never_adopted(self):
        result = run("AMOUNT")
        self.assertEqual(result["answer"]["recommendation"], "undetermined")
        self.assertTrue(any(n["review_status"] == "unresolved" and "$500" in n.get("text", "")
                            for n in result["graph"]["nodes"]))

    def test_replay_and_scorecard_binding(self):
        base = run()
        replay = run(model=Replay(base["model_calls"]))
        self.assertEqual(replay["graph"]["nodes"], base["graph"]["nodes"])
        self.assertEqual(replay["graph"]["edges"], base["graph"]["edges"])
        self.assertNotEqual(replay["task"]["run_id"], base["task"]["run_id"])
        for key in IDENTITY:
            self.assertEqual(replay["graph"][key], replay["scorecard"][key])
        invalid = copy.deepcopy(replay)
        invalid["answer"]["answer_version"] += 1
        with self.assertRaises(ValueError):
            markdown(invalid)

    def test_recorded_live_replay_still_reaches_dynamic_path(self):
        path = Path(__file__).resolve().parents[1] / "docs/dynamic-evidence/records/dyn01-model-replay.json"
        recorded = json.loads(path.read_text(encoding="utf-8"))
        task, tool = make_case(recorded["task"]["task_id"])
        result = Harness(Replay(recorded["model_calls"]), tool, budget=Budget(**recorded["budget"])).run(task)
        self.assertTrue(assess(result)["dynamic_path"])
        self.assertEqual(result["mode"], "replay")

    def test_loop_b_adapter_uses_team_query_signature(self):
        captured = []
        def query(source_type, customer_id, scenario="normal", page_token=None):
            captured.append((source_type, customer_id, scenario, page_token))
            return {"source_type": source_type, "pagination_complete": True}
        task, ext = make_case("CONTRACT-403")
        adapter = LoopBAdapter(query, ext)
        adapter(CONTRACT, task)
        adapter(MAINTENANCE, task, "page_2")
        self.assertEqual(captured, [(CONTRACT, task["customer_id"], "forbidden", None),
                                    (MAINTENANCE, task["customer_id"], "normal", "page_2")])
        self.assertEqual(adapter(TICKET, task)["source_type"], TICKET)

    def test_clarification_uses_no_tools(self):
        task, tool = make_case()
        task["incident_id"] = ""
        result = Harness(FixtureModel(), tool).run(task)
        self.assertEqual(result["graph"]["workflow_status"], "needs_clarification")
        self.assertEqual(result["usage"]["tool_calls"], 0)

    def test_prompt_baseline_receives_full_scan_without_graph(self):
        result = run(strategy="prompt")
        self.assertEqual([c["stage"] for c in result["model_calls"]], ["prompt"])
        self.assertEqual(result["usage"]["tool_calls"], 6)
        self.assertEqual(result["history"], [])
        payload = json.loads(result["model_calls"][0]["messages"][1]["content"])
        self.assertNotIn("task_id", payload)
        self.assertNotIn("gold", payload)

    def test_no_expand_does_not_silently_pass_new_contract(self):
        result = run(strategy="no_expand")
        self.assertEqual(result["answer"]["recommendation"], "undetermined")
        self.assertEqual(result["scorecard"]["level"], "证据不足")


if __name__ == "__main__":
    unittest.main()
