import json
import time
from pathlib import Path
from mock_tools import get_customer_contract, list_maintenance, build_escalation

BASE = Path(__file__).resolve().parent

def main():
    output = BASE / "demo_results"
    output.mkdir(exist_ok=True)
    log = []
    cases = [
        ("contract_found", "get_customer_contract", lambda: get_customer_contract("001")),
        ("contract_empty", "get_customer_contract", lambda: get_customer_contract("999")),
        ("maintenance_page1", "list_maintenance", lambda: list_maintenance("002")),
        ("maintenance_page2", "list_maintenance", lambda: list_maintenance("002", "page_2")),
        ("contract_403", "get_customer_contract", lambda: get_customer_contract("002", "forbidden")),
        ("contract_timeout", "get_customer_contract", lambda: get_customer_contract("002", "timeout")),
        ("contract_old", "get_customer_contract", lambda: get_customer_contract("002", "old_version")),
        ("opposite_materials", "get_customer_contract", lambda: get_customer_contract("002", "conflicting_materials")),
    ]
    for name, tool, call in cases:
        start = time.perf_counter()
        result = call()
        entry = {"case": name, "tool": tool, "result": result,
                 "elapsed_ms": round((time.perf_counter()-start)*1000, 3),
                 "simulated_cost_units": 1}
        log.append(entry)
        (output / (name + ".json")).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(name, result["tool_status"], "records:", len(result["records"]))
    (output / "call_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    escalation = build_escalation("demo_task_001", "002", "Loop A permission-denial demonstration", ["适用合同"], [], [log[4]], 1)
    (output / "escalation.json").write_text(json.dumps(escalation, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Results saved:", output)

if __name__ == "__main__":
    main()
