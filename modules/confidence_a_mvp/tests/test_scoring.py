import json
import unittest
from copy import deepcopy
from pathlib import Path

from confidence_a import ContractError, score_snapshot
from confidence_a.scoring import DEFAULT_POLICY

ROOT = Path(__file__).resolve().parents[1]


def example(name="01_supported"):
    return json.loads((ROOT / "examples" / f"{name}.snapshot.json").read_text(encoding="utf-8"))


class ScoringTests(unittest.TestCase):
    def test_three_meaningful_examples(self):
        for name, score, raw, allowed in (("01_supported", 100, 100, True),
                                          ("02_refuted", 100, 100, True),
                                          ("03_contract_unknown", 49, 80, False)):
            with self.subTest(name=name):
                card = score_snapshot(example(name))
                self.assertEqual((card["score"], card["raw_score"], card["may_present_definitive_decision"]),
                                 (score, raw, allowed))

    def test_metadata_failure_cannot_claim_resolved(self):
        for field in example()["obligations"][0]["checks"]:
            for value in (False, None):
                with self.subTest(field=field, value=value):
                    data = example()
                    data["obligations"][0]["checks"][field] = value
                    with self.assertRaises(ContractError):
                        score_snapshot(data)

    def test_unknown_and_conflict_preserve_risk_reasons(self):
        for status, reason in (("UNKNOWN", "PARTIAL_PAGE"), ("UNKNOWN", "ACCESS_DENIED"),
                               ("UNKNOWN", "TIMEOUT"), ("CONFLICT", "UNRESOLVED_CONFLICT")):
            with self.subTest(reason=reason):
                data = example()
                data["checker_decision"] = "UNDETERMINED"
                data["obligations"][0].update(status=status, reason_codes=[reason])
                card = score_snapshot(data)
                self.assertFalse(card["gate_passed"])
                self.assertEqual(card["blockers"][0]["reason_codes"], [reason])

    def test_definite_checker_decision_with_required_gap_is_error(self):
        data = example("03_contract_unknown")
        for decision in ("RECOMMEND_COMPENSATION", "DO_NOT_RECOMMEND"):
            data["checker_decision"] = decision
            with self.assertRaises(ContractError):
                score_snapshot(data)

    def test_optional_gap_does_not_force_abstention(self):
        data = example("03_contract_unknown")
        data["obligations"][0]["required_for_decision"] = False
        data["checker_decision"] = "DO_NOT_RECOMMEND"
        card = score_snapshot(data)
        self.assertTrue(card["may_present_definitive_decision"])
        self.assertEqual(card["score"], 80)
        self.assertEqual(len(card["gaps"]), 1)

    def test_procedurally_required_gap_still_blocks(self):
        data = example("03_contract_unknown")
        data["obligations"][0].update(required_for_decision=False, must_verify=True)
        self.assertFalse(score_snapshot(data)["gate_passed"])

    def test_undetermined_applicability_remains_in_denominator(self):
        data = example("03_contract_unknown")
        data["obligations"][0].update(applicability="UNDETERMINED", required_for_decision=False)
        card = score_snapshot(data)
        self.assertEqual(card["denominator_count"], 5)
        self.assertEqual(card["blockers"][0]["code"], "APPLICABILITY_UNDETERMINED")

    def test_proven_not_applicable_is_excluded_with_reason(self):
        data = example("03_contract_unknown")
        data["obligations"][0].update(applicability="NOT_APPLICABLE", status=None,
                                     applicability_reason="测试用：上游已证明当前分支不适用。")
        card = score_snapshot(data)
        self.assertEqual((card["score"], card["excluded_count"]), (100, 1))
        self.assertFalse(card["may_present_definitive_decision"])  # Checker has not decided.

    def test_no_applicable_obligations_is_not_full_score(self):
        data = example()
        data["checker_decision"] = "UNDETERMINED"
        for ob in data["obligations"]:
            ob.update(applicability="NOT_APPLICABLE", status=None)
        self.assertIsNone(score_snapshot(data)["score"])

    def test_no_required_obligations_is_blocked(self):
        data = example()
        data["checker_decision"] = "UNDETERMINED"
        for ob in data["obligations"]:
            ob["required_for_decision"] = False
        self.assertFalse(score_snapshot(data)["gate_passed"])

    def test_duplicate_ids_and_dangling_references_rejected(self):
        for kind in ("obligation", "evidence", "reference", "repeat_reference"):
            with self.subTest(kind=kind):
                data = example()
                if kind == "obligation":
                    data["obligations"].append(deepcopy(data["obligations"][0]))
                elif kind == "evidence":
                    data["evidence"].append(deepcopy(data["evidence"][0]))
                elif kind == "reference":
                    data["obligations"][0]["evidence_ids"] = ["NOT-FOUND"]
                else:
                    data["obligations"][0]["evidence_ids"] *= 2
                with self.assertRaises(ContractError):
                    score_snapshot(data)

    def test_more_evidence_does_not_inflate_score(self):
        data = example("03_contract_unknown")
        data["evidence"].append({"evidence_id": "EXTRA", "source_type": "CRM_CONTRACT_DB", "citation": "demo://extra"})
        self.assertEqual(score_snapshot(data)["score"], 49)

    def test_missing_fields_unknown_fields_and_wrong_types_rejected(self):
        for kind in ("missing", "extra", "boolean", "empty", "version"):
            with self.subTest(kind=kind):
                data = example()
                if kind == "missing":
                    del data["obligations"][0]["must_verify"]
                elif kind == "extra":
                    data["confidence"] = 100
                elif kind == "boolean":
                    data["obligations"][0]["required_for_decision"] = "false"
                elif kind == "empty":
                    data["obligations"] = []
                else:
                    data["schema_version"] = "future-version"
                with self.assertRaises(ContractError):
                    score_snapshot(data)

    def test_gate_not_bypassed_by_changing_display_cap(self):
        policy = deepcopy(DEFAULT_POLICY)
        policy["blocked_score_cap"] = 100
        card = score_snapshot(example("03_contract_unknown"), policy)
        self.assertEqual(card["score"], 80)
        self.assertFalse(card["may_present_definitive_decision"])

    def test_invalid_policy_numbers_rejected(self):
        for cap in (-1, 101, True, float("nan"), float("inf")):
            policy = deepcopy(DEFAULT_POLICY)
            policy["blocked_score_cap"] = cap
            with self.assertRaises(ContractError):
                score_snapshot(example(), policy)

    def test_deterministic_and_no_input_mutation(self):
        data = example("03_contract_unknown")
        before = deepcopy(data)
        self.assertEqual(score_snapshot(data), score_snapshot(data))
        self.assertEqual(data, before)

    def test_escalation_owned_by_loop(self):
        data = example("03_contract_unknown")
        data.update(process_state="ESCALATED", stop_reason="ACCESS_DENIED")
        card = score_snapshot(data)
        self.assertEqual(card["process_state"], "ESCALATED")
        self.assertFalse(card["may_present_definitive_decision"])


if __name__ == "__main__":
    unittest.main()
