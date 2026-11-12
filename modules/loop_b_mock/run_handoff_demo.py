"""Demonstrate Loop A requests. This is not an automatic controller."""
from pathlib import Path
import uuid
from loop_b_handoff import call_with_log, make_escalation, save_escalation


def main():
    folder = Path(__file__).resolve().parent / "handoff_results" / uuid.uuid4().hex
    log_path = folder / "calls.jsonl"
    task_id = "DEMO-TASK-001"
    entries = []
    # Explicit scripted requests stand in for Loop A; no automatic next-page choice.
    requests = [
        ("list_maintenance", {"customer_id": "002"}),
        ("list_maintenance", {"customer_id": "002", "page_token": "page_2"}),
        ("get_customer_contract", {"customer_id": "002", "scenario": "forbidden"}),
    ]
    for tool, parameters in requests:
        called = call_with_log(task_id, tool, parameters, log_path)
        entries.append(called["log_entry"])
        print(tool, called["response"]["tool_status"])
    # The demo explicitly supplies an escalation request, not an inferred policy.
    document = make_escalation(
        task_id, "002", "演示：Loop A要求因合同查询403转人工",
        [{"source_type": "CRM_CONTRACT_DB", "reason": "无权限取得合同"}],
        [], entries, 2,
        ["请有权限的人员取得客户002在故障时有效的合同。"],
    )
    path = save_escalation(document, folder)
    print("Log:", log_path)
    print("Escalation:", path)
    print("Three tool calls; attempted_rounds=2 is a DEMO value supplied by Loop A.")


if __name__ == "__main__":
    main()
