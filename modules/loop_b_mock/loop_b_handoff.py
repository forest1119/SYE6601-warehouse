"""Loop B integration helpers. No business judgment or stopping policy."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import json
import math
import time
import uuid
from mock_tools import get_customer_contract, list_maintenance
from ticket_tools import get_ticket

TOOLS = {
    "get_ticket": get_ticket,
    "get_customer_contract": get_customer_contract,
    "list_maintenance": list_maintenance,
}


def require_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + " must be nonempty text")


def call_with_log(task_id, tool_name, parameters, log_path, simulated_cost_units=1):
    """Call exactly one tool. No retry, pagination loop, or Checker inference.

    Returns {response, log_entry}; appends a JSONL record, never overwrites history.
    Persistence errors propagate to the caller instead of pretending logging succeeded.
    """
    require_text(task_id, "task_id")
    if tool_name not in TOOLS:
        raise ValueError("Tool is not registered: " + str(tool_name))
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be a dictionary")
    if type(simulated_cost_units) not in (int, float) or not math.isfinite(simulated_cost_units) or simulated_cost_units < 0:
        raise ValueError("simulated_cost_units must be a finite nonnegative number")
    request = deepcopy(parameters)
    started = datetime.now(timezone.utc).isoformat()
    begin = time.perf_counter()
    error = None
    try:
        response = TOOLS[tool_name](**deepcopy(request))
    except Exception as exc:
        # Tool-side exceptions are observable execution failures, not evidence absence.
        error = {"type": type(exc).__name__, "message": str(exc)}
        response = {"tool_status": "ERROR", "error_code": "TOOL_EXCEPTION",
                    "records": [], "pagination_complete": False,
                    "next_page_token": None}
    entry = {
        "schema_version": "loop-b-log-0.1-draft",
        "call_id": str(uuid.uuid4()), "task_id": task_id,
        "tool": tool_name, "parameters": request,
        "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_ms": round((time.perf_counter() - begin) * 1000, 3),
        "simulated_cost_units": simulated_cost_units,
        "cost_semantics": "synthetic units, not currency",
        "tool_status": response.get("tool_status", "ERROR"),
        "requested_page_token": request.get("page_token"),
        "next_page_token": response.get("next_page_token"),
        "pagination_complete": response.get("pagination_complete"),
        "response": deepcopy(response), "exception": error,
    }
    encoded = json.dumps(entry, ensure_ascii=False, allow_nan=False)
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(encoded + "\n")
    return {"response": response, "log_entry": entry}


def make_escalation(task_id, customer_id, reason, gaps, evidence_ids,
                    action_log, attempted_rounds, questions):
    """Format a handoff only after Loop A explicitly requests it.

    attempted_rounds is supplied by Loop A, not inferred from number of tool calls.
    No automatic decision to escalate, and no compensation decision.
    """
    for field, value in [("task_id", task_id), ("customer_id", customer_id), ("reason", reason)]:
        require_text(value, field)
    if type(attempted_rounds) is not int or attempted_rounds < 0:
        raise ValueError("attempted_rounds must be a nonnegative integer")
    for name, value in [("gaps", gaps), ("evidence_ids", evidence_ids),
                        ("action_log", action_log), ("questions", questions)]:
        if not isinstance(value, list):
            raise ValueError(name + " must be a list")
    if not questions or any(not isinstance(q, str) or not q.strip() for q in questions):
        raise ValueError("questions must contain nonempty human verification questions")
    if any(not isinstance(e, str) or not e.strip() for e in evidence_ids):
        raise ValueError("evidence_ids must contain nonempty strings")
    failed = []
    for entry in action_log:
        if not isinstance(entry, dict) or entry.get("task_id") != task_id:
            raise ValueError("action_log must contain only this task's wrapper log entries")
        status = entry.get("tool_status")
        if not isinstance(status, str) or not isinstance(entry.get("tool"), str):
            raise ValueError("action_log entry needs tool and tool_status")
        if status != "SUCCESS":
            failed.append({"call_id": entry.get("call_id"), "tool": entry["tool"],
                           "tool_status": status,
                           "error_code": entry.get("response", {}).get("error_code")})
    document = {
        "schema_version": "loop-b-escalation-0.1-draft",
        "task_id": task_id, "customer_id": customer_id,
        "escalation_requested_by": "LOOP_A", "reason": reason,
        "evidence_ids": deepcopy(evidence_ids), "unresolved_gaps": deepcopy(gaps),
        "failed_tools": failed, "attempted_rounds": attempted_rounds,
        "attempted_actions": deepcopy(action_log), "questions_for_human": list(questions),
    }
    json.dumps(document, ensure_ascii=False, allow_nan=False)
    return document


def save_escalation(document, output_dir):
    """Write a unique UTF-8 handoff file; previous handoffs are not overwritten."""
    encoded = json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False)
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ("escalation_" + uuid.uuid4().hex + ".json")
    with path.open("x", encoding="utf-8") as stream:
        stream.write(encoded)
    return path
