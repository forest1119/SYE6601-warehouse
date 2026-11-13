"""Independent synthetic gold and run-level evaluation. No gold is passed to Harness."""

from collections import Counter
from .matrix import MATRIX

GOLD = {
    "DYN-01": ("eligible", 90, 24), "NO-TICKET": ("eligible", 90, None),
    "LATE-TICKET": ("ineligible", 90, 24), "CONTRACT-403": ("undetermined", 60, None),
    "TICKET-403": ("undetermined", 90, 24), "MAINTENANCE": ("ineligible", 90, 24),
    "OLD-CONTRACT": ("undetermined", 60, None), "CONFLICT": ("undetermined", None, None),
    "REFERRAL": ("undetermined", 90, None), "AMOUNT": ("undetermined", 90, 24),
    "BOUNDARY": ("eligible", 90, 24), "SHORT-OUTAGE": ("ineligible", 90, 24),
    "EMPTY-CONTRACT": ("eligible", 60, None), "NEGATED": ("undetermined", 90, None),
    "MISSING-TICKET": ("ineligible", 90, 24),
}
FAULT = {"CONTRACT-403", "TICKET-403", "OLD-CONTRACT", "CONFLICT"}
GOLD.update({
    case_id: ("eligible" if duration >= 90 and boundary in ("early", "exact") else "ineligible", 90, hours)
    for case_id, (_, hours, boundary, duration) in MATRIX.items()
})


def assess(bundle):
    task_id = bundle["task"]["task_id"]
    expected, duration, deadline = GOLD[task_id]
    graph, answer, card = (bundle[k] for k in ("graph", "answer", "scorecard"))
    final_conditions = {n["condition"]: n.get("value") for n in graph["nodes"]
                        if n["id"].startswith("condition:") and "condition" in n}
    required = {k: v for k, v in (("duration_min", duration), ("ticket_deadline_hours", deadline))
                if v is not None}
    identified = sum(final_conditions.get(k) == v for k, v in required.items())
    trace = [r["source_type"] for r in bundle["tool_receipts"]]
    definitive = answer["recommendation"] in ("eligible", "ineligible")
    version_ok = all(graph[key] == answer[key] == card[key]
                     for key in ("task_id", "run_id", "graph_version", "answer_version"))
    resolve_ids = {r["call_id"]: {e["evidence_id"] for e in r["records"]} for r in bundle["tool_receipts"]}
    refs = card["evidence"]
    cited = sum(e["record_id"] in resolve_ids.get(e["call_id"], set()) for e in refs)
    # Compare against known raw policy requirements and the receipts actually obtained by this run.
    complete_sources = {r["source_type"] for r in bundle["tool_receipts"]
                        if r["tool_status"] == "SUCCESS" and r["pagination_complete"]}
    needed_sources = {"POLICY_DB", "INCIDENT_DB", "CRM_CONTRACT_DB", "MAINTENANCE_CALENDAR"}
    if deadline is not None:
        needed_sources.add("TICKET_DB")
    supported = (expected != "undetermined" and answer["recommendation"] == expected
                 and needed_sources <= complete_sources and identified == len(required)
                 and not card["blockers"] and version_ok)
    if bundle["strategy"] == "prompt":
        citations = answer.get("baseline_citations")
        citations = {c for c in citations if isinstance(c, str)} if isinstance(citations, list) else set()
        known = set().union(*resolve_ids.values())
        required_refs = {"I-DURATION", "P-THRESHOLD" if task_id == "EMPTY-CONTRACT" else "C-THRESHOLD"}
        if deadline is not None:
            required_refs.add("C-DEADLINE")
            if task_id != "MISSING-TICKET" and not (task_id in MATRIX and MATRIX[task_id][2] == "missing"):
                required_refs.add("T-01")
        if task_id == "MAINTENANCE":
            required_refs.add("M-01")
        supported = (expected != "undetermined" and answer["recommendation"] == expected
                     and needed_sources <= complete_sources and required_refs <= citations <= known)
        cited, refs = len(citations & known), citations
    discovered = bool(deadline is not None and final_conditions.get("ticket_deadline_hours") == deadline)
    initial_without_ticket = bool(bundle["history"]) and not any(
        n["id"] == "condition:ticket_deadline_hours" for n in bundle["history"][0]["nodes"])
    ordered = ("CRM_CONTRACT_DB" in trace and "TICKET_DB" in trace
               and trace.index("CRM_CONTRACT_DB") < trace.index("TICKET_DB"))
    ticket_action = next((a for a in bundle["action_log"] if a["source"] == "TICKET_DB"), {})
    prompted = any(g["target_source"] == "TICKET_DB" for g in ticket_action.get("candidate_gaps", []))
    dynamic_path = bool(initial_without_ticket and discovered and ordered and prompted and version_ok)
    accepted = [r for r in graph["checks"] if r["review_status"] == "accepted"]
    expected_relations = {("P-THRESHOLD", "duration_min", 60)}
    if task_id not in {"OLD-CONTRACT", "EMPTY-CONTRACT", "CONTRACT-403"}:
        expected_relations.add(("C-THRESHOLD", "duration_min", 90))
    if deadline is not None:
        expected_relations.add(("C-DEADLINE", "ticket_deadline_hours", deadline))
    if task_id == "CONFLICT":
        expected_relations.add(("CONFLICT-CONTRACT", "duration_min", 300))
    wrong = sum((r["record_id"], r["kind"], r["value"]) not in expected_relations for r in accepted)
    expected_gap = expected == "undetermined"
    return {"case_id": task_id, "run_id": answer["run_id"], "mode": bundle["mode"],
            "fault_origin": "injected" if task_id in FAULT else "none",
            "strategy": bundle["strategy"], "expected": expected, "actual": answer["recommendation"],
            "terminal_correct": expected == answer["recommendation"],
            "definitive": definitive, "assertion_supported": supported if definitive else None,
            "automatic_success": supported, "proper_escalation": expected_gap and graph["workflow_status"] == "escalated",
            "over_abstained": not expected_gap and not definitive,
            "critical_gap_missed": expected_gap and not card["blockers"],
            "critical_gap_expected": expected_gap, "critical_found": identified,
            "critical_expected": len(required) if bundle["strategy"] != "prompt" else 0,
            "accepted_relations": len(accepted), "wrong_accepted_relations": wrong,
            "resolvable_citations": cited, "citations": len(refs),
            "new_dependency_discovered": discovered, "targeted_dependency_action": discovered and prompted and ordered,
            "dynamic_path": dynamic_path and supported if task_id == "DYN-01" else None,
            "version_consistent": version_ok, "stop_reason": graph["stop_reason"], **bundle["usage"]}


def summarize(rows):
    def ratio(num, den):
        return {"numerator": num, "denominator": den, "value": num / den if den else None}

    return {
        "runs": len(rows),
        "terminal_accuracy": ratio(sum(r["terminal_correct"] for r in rows), len(rows)),
        "critical_condition_recall": ratio(sum(r["critical_found"] for r in rows), sum(r["critical_expected"] for r in rows)),
        "wrong_accepted_ratio": ratio(sum(r["wrong_accepted_relations"] for r in rows), sum(r["accepted_relations"] for r in rows)),
        "critical_gap_miss_rate": ratio(sum(r["critical_gap_missed"] for r in rows), sum(r["critical_gap_expected"] for r in rows)),
        "citation_resolvability": ratio(sum(r["resolvable_citations"] for r in rows), sum(r["citations"] for r in rows)),
        "unsupported_assertion_rate": ratio(sum(r["assertion_supported"] is False for r in rows), sum(r["definitive"] for r in rows)),
        "automatic_coverage": ratio(sum(r["definitive"] for r in rows), len(rows)),
        "automatic_success": ratio(sum(r["automatic_success"] for r in rows), len(rows)),
        "version_consistency": ratio(sum(r["version_consistent"] for r in rows), len(rows)),
        "dynamic_path_success": ratio(sum(r["dynamic_path"] is True for r in rows), sum(r["dynamic_path"] is not None for r in rows)),
        "proper_escalations": sum(r["proper_escalation"] for r in rows),
        "over_abstentions": sum(r["over_abstained"] for r in rows),
        "stops": dict(Counter(r["stop_reason"] for r in rows)),
        "resources": {field: {"measured": len(values), "total": sum(values) if values else None,
                              "mean": sum(values) / len(values) if values else None}
                      for field in ("tool_calls", "model_calls", "model_cost_usd", "tool_cost_units", "elapsed_ms")
                      for values in [[r[field] for r in rows if r[field] is not None]]},
    }
