"""Deterministic scoring of Checker declarations, never business inference."""

from .contracts import ContractError, DEFINITE, POLICY_SCHEMA, VERSION, validate, validate_snapshot

DEFAULT_POLICY = {
    "schema_version": VERSION,
    "policy_version": "equal-weight-demo-0.1",
    "status": "PROVISIONAL",
    "blocked_score_cap": 49,
    "description": "演示约定：义务等权；阻断时最多49分。非概率，非业务规则，待团队确认。",
}


def score_snapshot(snapshot, policy=None):
    """Return a new JSON-serializable card, without mutating either input."""
    validate_snapshot(snapshot)
    policy = DEFAULT_POLICY if policy is None else policy
    validate(policy, POLICY_SCHEMA, "policy")
    included = [o for o in snapshot["obligations"] if o["applicability"] != "NOT_APPLICABLE"]
    resolved = [o for o in included if o["status"] in ("SUPPORT", "REFUTE")]
    blockers = []
    gaps = []
    for ob in included:
        unresolved = ob["status"] in ("UNKNOWN", "CONFLICT")
        if unresolved:
            gaps.append({"obligation_id": ob["obligation_id"], "status": ob["status"],
                         "reason_codes": list(ob["reason_codes"]), "reason": ob["reason"]})
        code = None
        if ob["applicability"] == "UNDETERMINED":
            code = "APPLICABILITY_UNDETERMINED"
        elif unresolved and (ob["required_for_decision"] or ob["must_verify"]):
            code = "REQUIRED_OBLIGATION_UNRESOLVED"
        if code:
            blockers.append({"code": code, "obligation_id": ob["obligation_id"],
                             "reason_codes": list(ob["reason_codes"]), "reason": ob["reason"]})
    if not included:
        blockers.append({"code": "NO_APPLICABLE_OBLIGATIONS", "obligation_id": None,
                         "reason_codes": [], "reason": "没有可评分义务，需上游说明适用规则。"})
    if not any(o["required_for_decision"] or o["must_verify"] for o in included):
        blockers.append({"code": "NO_REQUIRED_OBLIGATIONS", "obligation_id": None,
                         "reason_codes": [], "reason": "未声明决策所需或程序必查义务。"})
    gate_passed = not blockers
    decision = snapshot["checker_decision"]
    if decision in DEFINITE and not gate_passed:
        raise ContractError("Checker definitive decision contradicts unresolved scoring prerequisites")
    raw = round(100 * len(resolved) / len(included), 2) if included else None
    score = min(raw, policy["blocked_score_cap"]) if raw is not None and blockers else raw
    rows = []
    for ob in snapshot["obligations"]:
        in_den = ob["applicability"] != "NOT_APPLICABLE"
        rows.append({"obligation_id": ob["obligation_id"], "statement": ob["statement"],
                     "status": ob["status"], "applicability": ob["applicability"],
                     "included_in_denominator": in_den,
                     "resolved": in_den and ob["status"] in ("SUPPORT", "REFUTE"),
                     "checks": dict(ob["checks"]), "evidence_ids": list(ob["evidence_ids"]),
                     "reason": ob["reason"], "applicability_reason": ob["applicability_reason"]})
    dimensions = {}
    for name in ("source_allowed", "scope_valid", "version_valid", "time_valid", "query_sufficient"):
        dimensions[name] = {"passed": sum(o["checks"][name] is True for o in included),
                            "denominator": len(included)}
    return {
        "schema_version": VERSION,
        **{k: snapshot[k] for k in ("task_id", "run_id", "snapshot_id", "rules_version", "synthetic_demo")},
        "scoring_policy_version": policy["policy_version"], "policy_status": policy["status"],
        "score_semantics": "已建模义务的证据充分性提示；不是答案正确概率。",
        "score": score, "raw_score": raw, "blocked_score_cap": policy["blocked_score_cap"],
        "gate_passed": gate_passed,
        "may_present_definitive_decision": gate_passed and decision in DEFINITE
            and snapshot["process_state"] != "ESCALATED",
        "checker_decision": decision, "process_state": snapshot["process_state"],
        "stop_reason": snapshot["stop_reason"],
        "resolved_count": len(resolved), "denominator_count": len(included),
        "excluded_count": len(snapshot["obligations"]) - len(included),
        "blockers": blockers, "gaps": gaps, "dimensions": dimensions, "obligations": rows,
        "evidence": [dict(e) for e in snapshot["evidence"]],
        "notes": ["SUPPORT 与 REFUTE 均可表示已查明。",
                  "诊断维度不重复计入总分；评分不选择工具、不生成补偿结论。",
                  "来源与时间适用性由 Checker 判断；本模块只验证其声明和引用自洽。"],
    }
