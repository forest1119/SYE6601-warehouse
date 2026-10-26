import json
import unittest
from copy import deepcopy
from pathlib import Path

from confidence_a import ContractError, evaluate_runs

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / "examples/runs.demo.json").read_text(encoding="utf-8"))


class MetricsTests(unittest.TestCase):
    def test_same_truth_different_run_support(self):
        groups = {g["scope"]["method"]: g for g in evaluate_runs(fixture())["groups"]}
        self.assertEqual(groups["dynamic"]["terminal_accuracy"]["value"], 1)
        self.assertEqual(groups["prompt_mock"]["terminal_accuracy"]["value"], 1)
        self.assertEqual(groups["dynamic"]["unsupported_answer_rate"]["value"], 0)
        self.assertEqual(groups["prompt_mock"]["unsupported_answer_rate"]["value"], 1)
        self.assertEqual(groups["prompt_mock"]["automatic_success_rate"]["value"], 0)

    def test_no_assertions_is_undefined_not_zero_risk(self):
        data = fixture()
        data["records"] = data["records"][:1]
        row = data["records"][0]
        row.update(actual_decision="UNDETERMINED", actual_escalated=True)
        row["assessment"].update(reference_decision="UNDETERMINED", expected_escalated=True,
                                  assertion_supported=None)
        group = evaluate_runs(data)["groups"][0]
        self.assertIsNone(group["unsupported_answer_rate"]["value"])
        self.assertEqual(group["automatic_coverage"]["value"], 0)
        self.assertEqual(group["proper_escalations"], 1)

    def test_missing_measurement_is_not_free(self):
        data = fixture()
        data["records"] = data["records"][:1]
        data["records"][0]["tool_calls"] = None
        group = evaluate_runs(data)["groups"][0]
        self.assertEqual(group["costs"]["tool_calls"], {"mean": None, "measured_count": 0, "missing_count": 1})

    def test_failed_run_remains_in_denominator(self):
        data = fixture()
        data["records"] = data["records"][:1]
        data["records"][0]["run_status"] = "FAILED"
        group = evaluate_runs(data)["groups"][0]
        self.assertEqual(group["terminal_accuracy"], {"numerator": 0, "denominator": 1, "value": 0})

    def test_strata_and_units_not_mixed(self):
        for field, value in (("fault_origin", "NATURAL"), ("synthetic_demo", False),
                             ("cost_unit", "USD"), ("permissions_id", "different")):
            with self.subTest(field=field):
                data = fixture()
                second = deepcopy(data["records"][0])
                second.update(run_id="another", **{field: value})
                data["records"] = [data["records"][0], second]
                self.assertEqual(len(evaluate_runs(data)["groups"]), 2)

    def test_missing_assessment_and_duplicate_runs_rejected(self):
        for kind in ("missing", "duplicate", "string_bool", "negative_cost"):
            data = fixture()
            if kind == "missing":
                del data["records"][0]["assessment"]["assertion_supported"]
            elif kind == "duplicate":
                data["records"].append(deepcopy(data["records"][0]))
            elif kind == "string_bool":
                data["records"][0]["assessment"]["assertion_supported"] = "false"
            else:
                data["records"][0]["cost_units"] = -1
            with self.assertRaises(ContractError):
                evaluate_runs(data)

    def test_empty_dataset(self):
        data = fixture()
        data["records"] = []
        self.assertEqual(evaluate_runs(data)["groups"], [])


if __name__ == "__main__":
    unittest.main()
