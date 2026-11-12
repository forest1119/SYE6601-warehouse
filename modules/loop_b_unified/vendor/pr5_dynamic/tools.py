"""Loop B adapter. Preserve raw receipts and isolate provider-specific field names."""

from dataclasses import dataclass
from datetime import datetime

CONTRACT = "CRM_CONTRACT_DB"
MAINTENANCE = "MAINTENANCE_CALENDAR"
POLICY = "POLICY_DB"
INCIDENT = "INCIDENT_DB"
TICKET = "TICKET_DB"
SOURCES = (POLICY, INCIDENT, CONTRACT, MAINTENANCE, TICKET)


def moment(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("Timezone required")
    return parsed


@dataclass(frozen=True)
class LoopBAdapter:
    query: object
    extensions: object = None

    def __call__(self, source, task, page=None):
        if source not in SOURCES:
            raise ValueError("Source is outside the tool allowlist")
        if source in (CONTRACT, MAINTENANCE) or self.extensions is None:
            scenario = task.get("scenarios", {}).get(source, "normal")
            return self.query(source, task["customer_id"], scenario=scenario, page_token=page)
        return self.extensions(source, task, page)


def applicable(record, source, task):
    try:
        scope = record.get("scope", {})
        expected_version = task.get("source_versions", {}).get(source)
        return (record["customer_id"] == task["customer_id"]
                and isinstance(scope, dict)
                and scope.get("customer_id", task["customer_id"]) == task["customer_id"]
                and scope.get("incident_id", task["incident_id"]) == task["incident_id"]
                and (record.get("incident_id") in (None, task["incident_id"]))
                and record["source_type"] == source and bool(record["version"])
                and (expected_version is None or record["version"] == expected_version)
                and bool(record["citation"])
                and moment(record["effective_from"]) <= moment(task["event_time"])
                <= moment(record["effective_to"]))
    except (ValueError, KeyError, TypeError, AttributeError):
        return False


class SyntheticTools:
    """Extend the team receipt shape with synthetic raw clauses and events."""

    def __init__(self, records):
        self.records = records

    def __call__(self, source, task, page=None):
        if source not in SOURCES:
            raise ValueError("Unknown tool")
        scenario = task.get("scenarios", {}).get(source, "normal")
        rows = [dict(row) for row in self.records.get(source, [])]
        status = {"forbidden": "FORBIDDEN", "timeout": "TIMEOUT"}.get(scenario, "SUCCESS")
        if scenario == "old_version":
            for row in rows:
                row["effective_to"] = "2024-12-31T00:00:00Z"
        if scenario == "conflicting_materials" and source == CONTRACT and rows:
            rows.append({**rows[0], "evidence_id": "CONFLICT-CONTRACT",
                         "statement": "The incident must last at least 300 minutes."})
        partial = (source == MAINTENANCE or scenario == "paged") and page is None
        return {"source_type": source, "customer_id": task["customer_id"],
                "incident_id": task["incident_id"], "tool_status": status,
                "records": rows if status == "SUCCESS" and not partial else [],
                "pagination_complete": status == "SUCCESS" and not partial,
                "next_page_token": "page_2" if partial and status == "SUCCESS" else None,
                "fetched_at": "2026-11-10T00:00:00Z",
                "cost_units": 1, "error_code": 403 if status == "FORBIDDEN" else None}
