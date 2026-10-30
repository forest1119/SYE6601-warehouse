import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent

def query(source_type, customer_id, scenario="normal", page_token=None):
    """返回原始模拟资料，不判断补偿资格；scenario仅供测试注入。"""
    result = {"source_type": source_type, "customer_id": customer_id,
              "tool_status": "SUCCESS", "records": [],
              "pagination_complete": False, "next_page_token": None,
              "fetched_at": datetime.now(timezone.utc).isoformat()}
    if scenario in ("forbidden", "timeout"):
        result.update(tool_status="FORBIDDEN" if scenario == "forbidden" else "TIMEOUT",
                      error_code=403 if scenario == "forbidden" else "SIMULATED_TIMEOUT")
        return result
    if scenario not in ("normal", "old_version", "conflicting_materials"):
        result.update(tool_status="ERROR", error_code="INVALID_SCENARIO")
        return result
    if source_type not in ("CRM_CONTRACT_DB", "MAINTENANCE_CALENDAR"):
        result.update(tool_status="ERROR", error_code="UNKNOWN_SOURCE")
        return result
    if source_type == "CRM_CONTRACT_DB" and page_token is not None:
        result.update(tool_status="ERROR", error_code="INVALID_PAGE_TOKEN")
        return result
    if source_type == "MAINTENANCE_CALENDAR" and page_token not in (None, "page_2"):
        result.update(tool_status="ERROR", error_code="INVALID_PAGE_TOKEN")
        return result
    filename = "contracts.json" if source_type == "CRM_CONTRACT_DB" else "maintenance.json"
    try:
        records = json.loads((BASE / "data" / filename).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        result.update(tool_status="ERROR", error_code="DATA_READ_ERROR")
        return result
    records = [r for r in records if r["customer_id"] == customer_id]
    if source_type == "MAINTENANCE_CALENDAR" and page_token is None:
        result["next_page_token"] = "page_2"
        return result
    if scenario == "old_version":
        for record in records:
            record.update(version="v0", effective_from="2024-01-01T00:00:00Z",
                          effective_to="2024-12-31T23:59:59Z")
    if scenario == "conflicting_materials" and records:
        other = dict(records[0])
        other.update(evidence_id=other["evidence_id"] + "_opposite",
                     citation=other["citation"] + "_opposite", statement="opposite synthetic statement")
        records[0]["statement"] = "original synthetic statement"
        records.append(other)
    result.update(records=records, pagination_complete=True)
    return result

def get_customer_contract(customer_id, scenario="normal"):
    return query("CRM_CONTRACT_DB", customer_id, scenario)

def list_maintenance(customer_id, page_token=None, scenario="normal"):
    return query("MAINTENANCE_CALENDAR", customer_id, scenario, page_token)

def build_escalation(task_id, customer_id, reason, gaps, evidence_ids, action_log, attempted_rounds):
    """由Loop A决定升级，再传入任务上下文。本函数只整理单据。"""
    return {"task_id": task_id, "customer_id": customer_id, "reason": reason,
            "missing_evidence": gaps, "evidence_ids": evidence_ids,
            "attempted_rounds": attempted_rounds, "attempted_actions": action_log,
            "failed_tools": [a["tool"] for a in action_log if a["result"]["tool_status"] != "SUCCESS"],
            "question_for_human": "请核实缺失资料及访问权限，并提供适用于该客户和故障时段的记录。"}
