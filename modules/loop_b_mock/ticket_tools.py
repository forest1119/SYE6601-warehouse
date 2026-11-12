"""Synthetic ticket queries for Loop B, compatible with PR5 source TICKET_DB.
Returns raw timestamps; never decides deadline compliance or compensation.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / "data" / "tickets.json"
SCENARIOS = {"normal", "forbidden", "timeout", "old_version", "paged",
             "missing_ticket", "late_ticket", "boundary"}


def get_ticket(customer_id, incident_id, scenario="normal", page_token=None):
    response = {"source_type": "TICKET_DB", "customer_id": customer_id,
                "incident_id": incident_id, "tool_status": "SUCCESS", "records": [],
                "pagination_complete": False, "next_page_token": None,
                "fetched_at": datetime.now(timezone.utc).isoformat(), "cost_units": 1}

    def fail(code, status="ERROR"):
        response.update(tool_status=status, error_code=code)
        return response

    if any(not isinstance(v, str) or not v.strip() for v in (customer_id, incident_id)):
        return fail("INVALID_QUERY_IDENTIFIERS")
    if not isinstance(scenario, str) or scenario not in SCENARIOS:
        return fail("INVALID_SCENARIO")
    if page_token is not None and (scenario != "paged" or page_token != "page_2"):
        return fail("INVALID_PAGE_TOKEN")
    if scenario == "forbidden":
        return fail(403, "FORBIDDEN")
    if scenario == "timeout":
        return fail("SIMULATED_TIMEOUT", "TIMEOUT")
    try:
        document = json.loads(DATA_PATH.read_text(encoding="utf-8-sig"))
        fixtures = document["fixtures"]
        # Reject malformed data instead of silently returning complete empty evidence.
        for fixture in fixtures.values():
            if not isinstance(fixture, list):
                raise ValueError("Fixture must be a list")
            for row in fixture:
                if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k].strip()
                        for k in ("customer_id", "incident_id", "evidence_id", "source_type")):
                    raise ValueError("Malformed ticket identity")
                if row["source_type"] != "TICKET_DB":
                    raise ValueError("Wrong source")
        key = scenario if scenario in ("missing_ticket", "late_ticket", "boundary") else "normal"
        rows = deepcopy(fixtures[key])
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return fail("DATA_READ_ERROR")
    rows = [r for r in rows if r["customer_id"] == customer_id and r["incident_id"] == incident_id]
    if scenario == "paged" and page_token is None:
        response["next_page_token"] = "page_2"
        return response
    if scenario == "old_version":
        for row in rows:
            row.update(version="v0", effective_from="2024-01-01T00:00:00Z",
                       effective_to="2024-12-31T23:59:59Z")
    response.update(records=rows, pagination_complete=True)
    return response


def extension_query(source, task, page=None):
    """For PR5 LoopBAdapter(query, extensions=extension_query).
    Existing query handles contract/maintenance; this extension only handles tickets.
    """
    if source != "TICKET_DB":
        raise ValueError("This extension supports only TICKET_DB; policy/incident require another provider")
    return get_ticket(task["customer_id"], task["incident_id"],
                      scenario=task.get("scenarios", {}).get(source, "normal"), page_token=page)
