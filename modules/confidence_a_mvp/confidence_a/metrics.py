"""Small offline evaluator. Assessments must be independent of online scores."""

from collections import defaultdict
from statistics import mean

from .contracts import DEFINITE, VERSION, validate_runs


def ratio(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None}


def summarize(rows):
    n = len(rows)
    asserted = [r for r in rows if r["actual_decision"] in DEFINITE]

    def correct(r):
        a = r["assessment"]
        return (r["run_status"] == "COMPLETED"
                and r["actual_decision"] == a["reference_decision"]
                and r["actual_escalated"] == a["expected_escalated"])

    automatic_success = sum(correct(r) and r["assessment"]["assertion_supported"] is True
                            and r["assessment"]["process_compliant"] for r in asserted)
    costs = {}
    for key in ("tool_calls", "cost_units", "latency_ms"):
        values = [r[key] for r in rows if r[key] is not None]
        costs[key] = {"mean": mean(values) if values else None,
                      "measured_count": len(values), "missing_count": n - len(values)}
    return {
        "n_runs": n, "run_ids": [r["run_id"] for r in rows],
        "terminal_accuracy": ratio(sum(correct(r) for r in rows), n),
        "assertion_accuracy": ratio(sum(correct(r) for r in asserted), len(asserted)),
        "unsupported_answer_rate": ratio(sum(r["assessment"]["assertion_supported"] is False
                                             for r in asserted), len(asserted)),
        "automatic_coverage": ratio(len(asserted), n),
        "automatic_success_rate": ratio(automatic_success, n),
        "escalation_rate": ratio(sum(r["actual_escalated"] for r in rows), n),
        "proper_escalations": sum(correct(r) and r["actual_escalated"]
                                  and r["assessment"]["process_compliant"] for r in rows),
        "failed_runs": sum(r["run_status"] == "FAILED" for r in rows), "costs": costs,
    }


def evaluate_runs(payload):
    validate_runs(payload)
    groups = defaultdict(list)
    # No mixing demo/real, different tools, rule versions, fault origins or methods.
    fields = ("method", "comparison_group", "dataset_version", "rules_version", "permissions_id",
              "execution_mode", "fault_origin", "synthetic_demo", "cost_unit", "rubric_version")
    for row in payload["records"]:
        groups[tuple(row["assessment"][k] if k == "rubric_version" else row[k] for k in fields)].append(row)
    return {"schema_version": VERSION, "n_records": len(payload["records"]),
            "groups": [{"scope": dict(zip(fields, key)), **summarize(rows)}
                       for key, rows in sorted(groups.items())],
            "notes": ["支持性标签必须由独立评审基于本次运行证据产生，不能读取评分卡。",
                      "失败运行保留在分母；缺测成本保留 null，均值只基于已测值。",
                      "此版本不自动输出方法间增益；比较前需配对相同案例及实验条件。",
                      "合成样例只验证接口，不是实验成绩。"]}
