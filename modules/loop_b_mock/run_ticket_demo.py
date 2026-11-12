"""Run locally in PyCharm. All outputs are synthetic, actual query executions."""
from pathlib import Path
import json
from datetime import datetime, timezone
from loop_b_handoff import call_with_log


def main():
    output = Path(__file__).resolve().parent / "ticket_results" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    cases = [
        ("ticket_found", {"customer_id": "C-DEMO", "incident_id": "I-DEMO"}),
        ("wrong_customer", {"customer_id": "OTHER", "incident_id": "I-DEMO"}),
        ("wrong_incident", {"customer_id": "C-DEMO", "incident_id": "OTHER"}),
    ]
    for scenario in ("forbidden", "timeout", "missing_ticket", "late_ticket", "boundary", "old_version"):
        cases.append((scenario, {"customer_id": "C-DEMO", "incident_id": "I-DEMO", "scenario": scenario}))
    for page in (None, "page_2"):
        cases.append(("paged_first" if page is None else "paged_second",
                      {"customer_id": "C-DEMO", "incident_id": "I-DEMO", "scenario": "paged", "page_token": page}))
    for name, parameters in cases:
        result = call_with_log("TICKET-DEMO-" + name, "get_ticket", parameters, output / "calls.jsonl")
        response = result["response"]
        (output / (name + ".json")).write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
        print(name, response["tool_status"], "records:", len(response["records"]))
    print("Results:", output)


if __name__ == "__main__":
    main()
