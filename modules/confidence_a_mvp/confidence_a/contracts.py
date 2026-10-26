"""Executable draft contracts, also exportable as JSON Schema.

Only the JSON Schema subset used below is implemented by validate().
Cross-reference and semantic checks follow structural validation.
"""

import math

VERSION = "0.1-draft"
DEFINITE = {"RECOMMEND_COMPENSATION", "DO_NOT_RECOMMEND"}
DECISIONS = sorted(DEFINITE) + ["UNDETERMINED"]
STATES = ["SUPPORT", "REFUTE", "UNKNOWN", "CONFLICT"]


class ContractError(ValueError):
    """Invalid or internally inconsistent input; no score should be displayed."""


def obj(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def arr(items, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum}


TEXT = {"type": "string", "minLength": 1}
BOOL = {"type": "boolean"}
IDS = {**arr(TEXT), "uniqueItems": True}
NUMBER = {"type": "number", "minimum": 0}
NULL_NUMBER = {"type": ["number", "null"], "minimum": 0}
CHECKS = obj({name: {"type": ["boolean", "null"]} for name in (
    "source_allowed", "scope_valid", "version_valid", "time_valid", "query_sufficient")})

SNAPSHOT_SCHEMA = obj({
    "schema_version": {"const": VERSION},
    "task_id": TEXT, "run_id": TEXT, "snapshot_id": TEXT,
    "rules_version": TEXT,
    "synthetic_demo": BOOL,
    "checker_decision": {"enum": DECISIONS},
    "process_state": {"enum": ["RUNNING", "COMPLETED", "ESCALATED"]},
    "stop_reason": {"type": ["string", "null"]},
    "obligations": arr(obj({
        "obligation_id": TEXT, "rule_id": TEXT, "statement": TEXT,
        "applicability": {"enum": ["APPLICABLE", "NOT_APPLICABLE", "UNDETERMINED"]},
        "applicability_reason": TEXT,
        "required_for_decision": BOOL, "must_verify": BOOL,
        "status": {"enum": STATES + [None]},
        "checks": CHECKS,
        "evidence_ids": IDS, "reason_codes": IDS, "reason": TEXT,
    }), 1),
    "evidence": arr(obj({"evidence_id": TEXT, "source_type": TEXT, "citation": TEXT})),
})

POLICY_SCHEMA = obj({
    "schema_version": {"const": VERSION}, "policy_version": TEXT,
    "status": {"enum": ["PROVISIONAL", "TEAM_CONFIRMED"]},
    "blocked_score_cap": {"type": "number", "minimum": 0, "maximum": 100},
    "description": TEXT,
})

RUN_SCHEMA = obj({
    "case_id": TEXT, "task_id": TEXT, "run_id": TEXT, "method": TEXT,
    "comparison_group": TEXT,
    "dataset_version": TEXT, "rules_version": TEXT, "permissions_id": TEXT,
    "execution_mode": {"enum": ["SIMULATED", "REAL_MODEL", "DETERMINISTIC"]},
    "fault_origin": {"enum": ["NONE", "INJECTED", "NATURAL"]},
    "synthetic_demo": BOOL,
    "run_status": {"enum": ["COMPLETED", "FAILED"]},
    "actual_decision": {"enum": DECISIONS}, "actual_escalated": BOOL,
    "tool_calls": {"type": ["integer", "null"], "minimum": 0},
    "cost_units": NULL_NUMBER, "latency_ms": NULL_NUMBER, "cost_unit": TEXT,
    "assessment": obj({
        "assessment_id": TEXT, "assessor": TEXT, "rubric_version": TEXT,
        "evidence_snapshot_id": TEXT,
        "reference_decision": {"enum": DECISIONS},
        "expected_escalated": BOOL,
        "assertion_supported": {"type": ["boolean", "null"]},
        "process_compliant": BOOL, "reason": TEXT,
    }),
})

RUNS_SCHEMA = obj({"schema_version": {"const": VERSION}, "records": arr(RUN_SCHEMA)})

RISK_SCHEMA = obj({"code": TEXT, "obligation_id": {"type": ["string", "null"]},
                   "reason_codes": IDS, "reason": TEXT})
SCORECARD_SCHEMA = obj({
    "schema_version": {"const": VERSION},
    **{key: TEXT for key in ("task_id", "run_id", "snapshot_id", "rules_version", "scoring_policy_version")},
    "synthetic_demo": BOOL, "policy_status": {"enum": ["PROVISIONAL", "TEAM_CONFIRMED"]},
    "score_semantics": TEXT,
    "score": {"type": ["number", "null"], "minimum": 0, "maximum": 100},
    "raw_score": {"type": ["number", "null"], "minimum": 0, "maximum": 100},
    "blocked_score_cap": {"type": "number", "minimum": 0, "maximum": 100},
    "gate_passed": BOOL, "may_present_definitive_decision": BOOL,
    "checker_decision": {"enum": DECISIONS},
    "process_state": {"enum": ["RUNNING", "COMPLETED", "ESCALATED"]},
    "stop_reason": {"type": ["string", "null"]},
    **{key: {"type": "integer", "minimum": 0} for key in ("resolved_count", "denominator_count", "excluded_count")},
    "blockers": arr(RISK_SCHEMA),
    "gaps": arr(obj({"obligation_id": TEXT, "status": {"enum": ["UNKNOWN", "CONFLICT"]},
                      "reason_codes": IDS, "reason": TEXT})),
    "dimensions": obj({key: obj({"passed": {"type": "integer", "minimum": 0},
                                  "denominator": {"type": "integer", "minimum": 0}})
                       for key in CHECKS["properties"]}),
    "evidence": SNAPSHOT_SCHEMA["properties"]["evidence"],
    "obligations": arr(obj({"obligation_id": TEXT, "statement": TEXT,
                            "status": {"enum": STATES + [None]},
                            "applicability": {"enum": ["APPLICABLE", "NOT_APPLICABLE", "UNDETERMINED"]},
                            "included_in_denominator": BOOL, "resolved": BOOL, "checks": CHECKS,
                            "evidence_ids": IDS, "reason": TEXT, "applicability_reason": TEXT}), 1),
    "notes": arr(TEXT),
})


def validate(value, schema, path="$"):
    """Strict validation: rejects bool-as-number, nonfinite numbers, and unknown keys."""
    if "const" in schema and value != schema["const"]:
        raise ContractError(f"{path}: expected {schema['const']!r}")
    if "enum" in schema and not any(type(value) is type(x) and value == x for x in schema["enum"]):
        raise ContractError(f"{path}: value {value!r} is not in enum")
    types = schema.get("type", [])
    if isinstance(types, str):
        types = [types]
    matches = {
        "object": isinstance(value, dict), "array": isinstance(value, list),
        "string": isinstance(value, str), "boolean": type(value) is bool,
        "integer": type(value) is int,
        "number": type(value) in (int, float) and math.isfinite(value),
        "null": value is None,
    }
    if types and not any(matches[t] for t in types):
        raise ContractError(f"{path}: expected {types}")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        missing = set(schema.get("required", [])) - value.keys()
        extra = value.keys() - properties.keys()
        if missing or (extra and schema.get("additionalProperties") is False):
            raise ContractError(f"{path}: missing={sorted(missing)}, unknown={sorted(extra)}")
        for key, val in value.items():
            if key in properties:
                validate(val, properties[key], f"{path}.{key}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise ContractError(f"{path}: too few items")
        for i, val in enumerate(value):
            validate(val, schema["items"], f"{path}[{i}]")
        if schema.get("uniqueItems") and any(val in value[:i] for i, val in enumerate(value)):
            raise ContractError(f"{path}: duplicate entries")
    if isinstance(value, str) and "minLength" in schema and not value.strip():
        raise ContractError(f"{path}: nonblank string required")
    if type(value) in (int, float):
        if value < schema.get("minimum", -math.inf) or value > schema.get("maximum", math.inf):
            raise ContractError(f"{path}: numeric value outside permitted range")


def unique_index(rows, key, path):
    result = {}
    for row in rows:
        if row[key] in result:
            raise ContractError(f"{path}: duplicate {key}={row[key]}")
        result[row[key]] = row
    return result


def validate_snapshot(snapshot):
    validate(snapshot, SNAPSHOT_SCHEMA, "snapshot")
    obligations = unique_index(snapshot["obligations"], "obligation_id", "obligations")
    evidence = unique_index(snapshot["evidence"], "evidence_id", "evidence")
    for oid, ob in obligations.items():
        if set(ob["evidence_ids"]) - evidence.keys():
            raise ContractError(f"{oid}: evidence reference not found")
        applicability, status = ob["applicability"], ob["status"]
        if applicability == "NOT_APPLICABLE":
            if status is not None:
                raise ContractError(f"{oid}: not-applicable obligation must have null status")
        elif applicability == "UNDETERMINED":
            if status != "UNKNOWN":
                raise ContractError(f"{oid}: undetermined applicability requires UNKNOWN")
        elif status is None:
            raise ContractError(f"{oid}: applicable obligation requires four-state status")
        if status in ("SUPPORT", "REFUTE"):
            if not ob["evidence_ids"] or not all(x is True for x in ob["checks"].values()):
                raise ContractError(f"{oid}: resolved status requires references and all validated checks")
        if status in ("UNKNOWN", "CONFLICT") and not ob["reason_codes"]:
            raise ContractError(f"{oid}: unresolved status requires a reason code")
        if status == "CONFLICT" and not ob["evidence_ids"]:
            raise ContractError(f"{oid}: conflict requires evidence references")
    if snapshot["process_state"] != "RUNNING" and not snapshot["stop_reason"]:
        raise ContractError("terminal process_state requires stop_reason")
    if snapshot["process_state"] == "ESCALATED" and snapshot["checker_decision"] in DEFINITE:
        raise ContractError("escalated snapshot cannot present a definitive recommendation in this MVP")
    return snapshot


def validate_runs(payload):
    validate(payload, RUNS_SCHEMA, "runs")
    unique_index(payload["records"], "run_id", "records")
    for row in payload["records"]:
        a = row["assessment"]
        asserted = row["actual_decision"] in DEFINITE
        if asserted and a["assertion_supported"] is None:
            raise ContractError(f"{row['run_id']}: asserted decision requires independent support assessment")
        if not asserted and a["assertion_supported"] is not None:
            raise ContractError(f"{row['run_id']}: no assertion; support assessment must be null")
        if row["actual_escalated"] and asserted:
            raise ContractError(f"{row['run_id']}: escalation and assertion cannot coexist in MVP")
        if a["expected_escalated"] and a["reference_decision"] in DEFINITE:
            raise ContractError(f"{row['run_id']}: reference escalation must be UNDETERMINED")
    return payload


def exported_schemas():
    return {name: {"$schema": "https://json-schema.org/draft/2020-12/schema",
                   "title": name, **schema} for name, schema in {
        "snapshot": SNAPSHOT_SCHEMA, "policy": POLICY_SCHEMA, "runs": RUNS_SCHEMA,
        "scorecard": SCORECARD_SCHEMA,
    }.items()}
