"""Regenerate explicitly synthetic examples. Run from the workspace root."""

import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from confidence_a.contracts import VERSION, exported_schemas
from confidence_a.scoring import DEFAULT_POLICY, score_snapshot
from confidence_a.metrics import evaluate_runs


def write(relative, value):
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def base_snapshot():
    specs = [
        ("CONTRACT", "适用合同条款允许本次事故补偿", "CRM_CONTRACT_DB"),
        ("DURATION", "本次事故的有效时长达到适用阈值", "MONITORING_SYSTEM"),
        ("MAINTENANCE", "本次事故不存在适用的维护排除条件", "MAINTENANCE_CALENDAR"),
        ("CAUSE", "本次事故不属于已建模的责任免责情形", "INCIDENT_REVIEW"),
        ("PLAN", "本次事故对应套餐在适用范围内", "PLAN_DB"),
    ]
    obligations, evidence = [], []
    for name, statement, source in specs:
        eid = f"DEMO-E-{name}"
        obligations.append({
            "obligation_id": f"DEMO-O-{name}", "rule_id": "DEMO-RULE-ONLY",
            "statement": statement, "applicability": "APPLICABLE",
            "applicability_reason": "仅为接入演示手写的适用义务，不代表01A正式规则。",
            "required_for_decision": True, "must_verify": False, "status": "SUPPORT",
            "checks": {k: True for k in ("source_allowed", "scope_valid", "version_valid", "time_valid", "query_sufficient")},
            "evidence_ids": [eid], "reason_codes": [], "reason": "联调占位：Checker声明已由适用证据查明。",
        })
        evidence.append({"evidence_id": eid, "source_type": source,
                         "citation": f"demo://fixture/{name.lower()}（合成引用，无真实业务凭证）"})
    return {"schema_version": VERSION, "task_id": "DEMO-TASK-01", "run_id": "DEMO-RUN-01",
            "snapshot_id": "DEMO-SNAPSHOT-01", "rules_version": "demo-only-not-01a",
            "synthetic_demo": True, "checker_decision": "RECOMMEND_COMPENSATION",
            "process_state": "COMPLETED", "stop_reason": "DEMO_CHECKER_RESOLVED",
            "obligations": obligations, "evidence": evidence}


def main():
    first = base_snapshot()
    second = deepcopy(first)
    second.update(task_id="DEMO-TASK-02", run_id="DEMO-RUN-02", snapshot_id="DEMO-SNAPSHOT-02",
                  checker_decision="DO_NOT_RECOMMEND")
    second["obligations"][0].update(status="REFUTE", reason="演示合同条款明确不允许本次补偿。")
    third = deepcopy(first)
    third.update(task_id="DEMO-TASK-03", run_id="DEMO-RUN-03", snapshot_id="DEMO-SNAPSHOT-03",
                 checker_decision="UNDETERMINED", process_state="RUNNING", stop_reason=None)
    third["obligations"][0].update(status="UNKNOWN", evidence_ids=[], reason_codes=["NOT_QUERIED"],
                                  reason="尚未取得适用合同，其他四项查明不能填补此缺口。")
    third["obligations"][0]["checks"] = {k: None for k in third["obligations"][0]["checks"]}
    third["evidence"] = third["evidence"][1:]
    for name, snapshot in zip(("01_supported", "02_refuted", "03_contract_unknown"), (first, second, third)):
        write(f"examples/{name}.snapshot.json", snapshot)
        write(f"examples/{name}.scorecard.json", score_snapshot(snapshot))
    write("policy.demo.json", DEFAULT_POLICY)
    for name, schema in exported_schemas().items():
        write(f"schemas/{name}.schema.json", schema)
    # Same case and reference decision, but one run has proof and one merely guesses correctly.
    rows = []
    for i, (method, supported, calls) in enumerate((("dynamic", True, 2), ("prompt_mock", False, 1)), 1):
        rows.append({
            "case_id": "DEMO-CASE-SAME-WORLD", "task_id": "DEMO-EVAL-TASK",
            "run_id": f"DEMO-EVAL-RUN-{i}", "method": method,
            "comparison_group": "demo-identical-environment", "dataset_version": "demo-0.1",
            "rules_version": "demo-only-not-01a", "permissions_id": "demo-permissions",
            "execution_mode": "SIMULATED", "fault_origin": "INJECTED", "synthetic_demo": True,
            "run_status": "COMPLETED", "actual_decision": "DO_NOT_RECOMMEND", "actual_escalated": False,
            "tool_calls": calls, "cost_units": float(calls), "latency_ms": None, "cost_unit": "demo_unit",
            "assessment": {
                "assessment_id": f"DEMO-ASSESSMENT-{i}", "assessor": "handwritten-fixture-not-experiment",
                "rubric_version": "demo-rubric-0.1", "evidence_snapshot_id": f"DEMO-EVAL-SNAPSHOT-{i}",
                "reference_decision": "DO_NOT_RECOMMEND", "expected_escalated": False,
                "assertion_supported": supported, "process_compliant": supported,
                "reason": "手写演示：已取得合同。" if supported else "手写演示：未取得合同，碰巧猜对不补偿。",
            },
        })
    runs = {"schema_version": VERSION, "records": rows}
    write("examples/runs.demo.json", runs)
    write("examples/metrics.demo.json", evaluate_runs(runs))
    print("Generated 3 snapshots/cards, schemas, policy and illustrative metrics. No real experiment run.")


if __name__ == "__main__":
    main()
