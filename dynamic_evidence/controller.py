"""Loop A and the integration boundary. Every run gets an isolated trace."""

import json
import math
from dataclasses import asdict, dataclass
from time import monotonic
from uuid import uuid4

from . import VERSION
from .graph import PROMPT_VERSION, build_candidate_graph, received, review_graph, source_records
from .models import ModelError
from .report import LABELS, scorecard
from .tools import INCIDENT, MAINTENANCE, POLICY, SOURCES, TICKET, moment
from .baselines import ORDINARY_PROMPT, configured_builder


class RunLimit(RuntimeError):
    pass


@dataclass(frozen=True)
class Budget:
    max_rounds: int = 3
    max_tool_calls: int = 10
    max_model_calls: int = 10
    max_cost: float = 0.10
    max_elapsed: float = 150
    max_graph_nodes: int = 100
    max_graph_updates: int = 8

    def __post_init__(self):
        for key, value in asdict(self).items():
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError(f"Invalid budget {key}")
            if key not in ("max_cost", "max_elapsed") and type(value) is not int:
                raise ValueError(f"Integer required for {key}")


class Harness:
    def __init__(self, model, tool, *, budget=None, builder=build_candidate_graph, reviewer=review_graph):
        self.model, self.tool = model, tool
        self.budget = budget or Budget()
        self.builder, self.reviewer = builder, reviewer

    def run(self, task, *, strategy="dynamic"):
        if strategy not in ("dynamic", "fixed", "no_expand", "prompt", "configured"):
            raise ValueError("Unknown strategy")
        task = {**task, "run_id": str(uuid4())}
        start = monotonic()
        receipts, calls, actions, history, cache, proposals = [], [], [], [], {}, []
        cost = 0.0
        known_cost = True
        rounds = 0
        stop, workflow = "COMPLETED", "completed"
        graph = None
        ordinary_answer = None

        def remaining():
            left = self.budget.max_elapsed - (monotonic() - start)
            if left <= 0:
                raise RunLimit("ELAPSED_LIMIT")
            return left

        def model(stage, system, data):
            nonlocal cost, known_cost
            timeout = remaining()
            if len(calls) >= self.budget.max_model_calls:
                raise RunLimit("MODEL_CALL_LIMIT")
            if not known_cost or cost >= self.budget.max_cost:
                raise RunLimit("COST_LIMIT" if known_cost else "MODEL_COST_UNAVAILABLE")
            messages = [{"role": "system", "content": system},
                        {"role": "user", "content": json.dumps(data, ensure_ascii=False, sort_keys=True)}]
            entry = {"call_id": f"model-{len(calls)+1}", "stage": stage, "messages": messages}
            calls.append(entry)
            try:
                response = self.model(stage, messages, min(timeout, 45))
                entry["response"] = response
                usage = response.get("usage") or {}
                amount = usage.get("cost")
                if type(amount) in (int, float) and math.isfinite(amount) and amount >= 0:
                    cost += amount
                else:
                    known_cost = False
                if cost > self.budget.max_cost:
                    raise RunLimit("COST_LIMIT_AFTER_CALL")
                remaining()
                if response.get("finish_reason") in ("length", "content_filter"):
                    raise ModelError("Incomplete model output")
                content = json.loads(response["raw_output"])
                if not isinstance(content, dict):
                    raise ValueError("Model output must be a JSON object")
                return content
            except (ModelError, ValueError, TypeError, KeyError) as error:
                entry["error"] = str(error) if isinstance(error, ModelError) else type(error).__name__
                raise ModelError(entry["error"]) from None

        def fetch(source):
            action = {"source": source, "round": rounds,
                      "start_graph_version": graph["graph_version"] if graph else 0,
                      "candidate_gaps": graph["gaps"] if graph else [],
                      "call_ids": [], "model_call_ids": []}
            actions.append(action)
            page = None
            pages = set()
            retried = False
            while True:
                remaining()
                if len(receipts) >= self.budget.max_tool_calls:
                    raise RunLimit("TOOL_CALL_LIMIT")
                cid = f"tool-{len(receipts)+1}"
                then = monotonic()
                try:
                    raw = self.tool(source, task, page)
                    if not isinstance(raw, dict):
                        raise ValueError("Tool output must be an object")
                    receipt = {**raw, "task_id": task["task_id"], "run_id": task["run_id"],
                               "call_id": cid, "elapsed_ms": round((monotonic()-then)*1000, 2),
                               "requested_page": page, "requested_source": source,
                               "arguments": {"customer_id": task["customer_id"],
                                             "incident_id": task["incident_id"], "event_time": task["event_time"],
                                             "page_token": page}}
                    if (raw.get("source_type") != source or raw.get("customer_id") != task["customer_id"]
                            or raw.get("incident_id", task["incident_id"]) != task["incident_id"]
                            or not isinstance(raw.get("records"), list)
                            or any(not isinstance(r, dict) or not isinstance(r.get("evidence_id"), str)
                                   or not r["evidence_id"] for r in raw["records"])
                            or type(raw.get("pagination_complete")) is not bool
                            or raw.get("tool_status") not in ("SUCCESS", "FORBIDDEN", "TIMEOUT", "ERROR")):
                        raise ValueError("Invalid tool receipt")
                except Exception as error:
                    receipt = {"source_type": source, "customer_id": task["customer_id"], "call_id": cid,
                               "records": [], "tool_status": "ERROR", "pagination_complete": False,
                               "error_code": type(error).__name__, "requested_page": page,
                               "elapsed_ms": round((monotonic()-then)*1000, 2),
                               "task_id": task["task_id"], "run_id": task["run_id"]}
                receipts.append(receipt)
                action["call_ids"].append(cid)
                status = receipt["tool_status"]
                if status == "TIMEOUT" and not retried:
                    retried = True
                    continue
                if status != "SUCCESS":
                    return action
                if receipt["pagination_complete"] and not receipt.get("next_page_token"):
                    return action
                cursor = receipt.get("next_page_token")
                if receipt["pagination_complete"] or not isinstance(cursor, str) or not cursor or cursor in pages:
                    receipt["pagination_complete"] = False
                    receipt["pagination_error"] = "INVALID_OR_REPEATED_CURSOR"
                    return action
                page = cursor
                pages.add(page)
                retried = False

        def publish(action=None, *, expand=True):
            nonlocal graph
            remaining()
            if len(history) >= self.budget.max_graph_updates:
                raise RunLimit("GRAPH_UPDATE_LIMIT")
            from_call = len(calls)
            records = source_records(receipts, task)
            builder = configured_builder if strategy == "configured" else self.builder
            proposal = builder(task, records, graph, task.get("candidate_answer"), model) if expand else None
            if proposal is not None:
                proposals.append({"base_graph_version": graph["graph_version"] if graph else 0,
                                  "proposal": proposal})
            try:
                updated = self.reviewer(task, graph, proposal, receipts, model, cache)
            except ValueError as error:
                raise ModelError("Invalid proposal structure") from error
            if len(updated["nodes"]) > self.budget.max_graph_nodes:
                raise RunLimit("GRAPH_NODE_LIMIT")
            graph = updated
            history.append(graph)
            if action is not None:
                for change in graph["changes"]:
                    change["trigger_call_ids"] = list(action["call_ids"])
                action.update(model_call_ids=[x["call_id"] for x in calls[from_call:]],
                              graph_version=graph["graph_version"], changes=graph["changes"])

        try:
            if not all(isinstance(task.get(k), str) and task[k].strip()
                       for k in ("task_id", "question", "customer_id", "incident_id", "event_time")):
                workflow = "needs_clarification"
                raise RunLimit("MISSING_TASK_FIELDS")
            try:
                moment(task["event_time"])
            except ValueError:
                workflow = "needs_clarification"
                raise RunLimit("INVALID_EVENT_TIME")
            if strategy in ("fixed", "prompt"):
                for source in SOURCES:
                    fetch(source)
                if strategy == "fixed":
                    publish(actions[-1])
                else:
                    # Both full-scan methods see the same tools, pagination, and raw business fields.
                    sanitized = [{k: r[k] for k in ("source_type", "tool_status", "pagination_complete", "records")}
                                 for r in receipts]
                    ordinary_answer = model("prompt", ORDINARY_PROMPT, {
                        "question": task["question"], "event_time": task["event_time"],
                        "candidate_answer": task.get("candidate_answer"), "receipts": sanitized})
                    if ordinary_answer.get("recommendation") not in ("eligible", "ineligible", "undetermined"):
                        raise ModelError("Invalid baseline recommendation")
            else:
                for source in (POLICY, INCIDENT, MAINTENANCE):
                    fetch(source)
                publish(actions[-1])
                while True:
                    gaps = [g for g in graph["gaps"] if g["critical"] or g["must_verify"]]
                    targets = [g["target_source"] for g in sorted(gaps, key=lambda g: not g["must_verify"])
                               if g["target_source"] and not received(receipts, g["target_source"])]
                    if not targets:
                        break
                    if rounds >= self.budget.max_rounds:
                        raise RunLimit("ROUND_LIMIT")
                    source = targets[0]
                    if any(r["source_type"] == source for r in receipts):
                        raise RunLimit("TOOL_BLOCKED")
                    rounds += 1
                    action = fetch(source)
                    publish(action, expand=strategy != "no_expand")
            if graph and any(g["critical"] or g["must_verify"] for g in graph["gaps"]):
                stop, workflow = "UNRESOLVED_GAPS", "escalated"
        except (RunLimit, ModelError) as error:
            stop = str(error) if isinstance(error, RunLimit) else "MODEL_OR_PROPOSAL_FAILED"
            if workflow != "needs_clarification":
                workflow = "escalated" if isinstance(error, ModelError) or stop == "TOOL_BLOCKED" else "completed"

        if graph is None:
            graph = {"task_id": task.get("task_id"), "run_id": task["run_id"], "graph_version": 0,
                     "nodes": [], "edges": [], "checks": [], "coverage": [], "gaps": [], "changes": [],
                     "recommendation": "undetermined", "scope_declaration": "暂无通过审核的证据快照。"}
        if stop not in ("COMPLETED", "UNRESOLVED_GAPS"):
            gap = {"gap_type": "TOOL_BLOCKED" if stop == "TOOL_BLOCKED" else "UNRESOLVED_SEMANTICS",
                   "reason": stop, "target_source": None, "critical": True, "must_verify": True,
                   "affected_claim_ids": ["claim-eligibility"]}
            graph = {**graph, "recommendation": "undetermined", "gaps": graph["gaps"] + [gap]}
        for receipt in receipts if strategy != "prompt" else ():
            if receipt["tool_status"] == "FORBIDDEN":
                source = receipt["source_type"]
                is_required = source != TICKET or any(g["target_source"] == source for g in graph["gaps"])
                if is_required:
                    workflow, stop = "escalated", "ACCESS_DENIED"
                    blocked = {"gap_type": "TOOL_BLOCKED", "reason": f"{source} 403",
                               "target_source": source, "critical": True, "must_verify": True,
                               "affected_claim_ids": ["claim-eligibility"]}
                    graph = {**graph, "recommendation": "undetermined", "gaps": graph["gaps"] + [blocked]}
        graph = {**graph, "answer_version": 1, "workflow_status": workflow, "stop_reason": stop}
        answer = {k: graph[k] for k in ("task_id", "run_id", "graph_version", "answer_version", "recommendation")}
        if ordinary_answer is not None:
            answer["recommendation"] = ordinary_answer["recommendation"]
            answer["baseline_explanation"] = ordinary_answer.get("reason")
            answer["baseline_citations"] = ordinary_answer.get("evidence_ids")
        answer["text"] = LABELS[answer["recommendation"]]
        answer["claim_ids"] = [n["id"] for n in graph["nodes"] if n["type"] == "claim"
                               and n["review_status"] == "accepted"]
        escalation = None
        if workflow == "escalated":
            escalation = {k: graph[k] for k in ("task_id", "run_id", "graph_version", "answer_version",
                                                 "recommendation", "workflow_status", "stop_reason")}
            escalation.update(gaps=graph["gaps"], attempted_rounds=rounds, tool_calls=len(receipts),
                              sources=list(dict.fromkeys(r["source_type"] for r in receipts)),
                              failed_call_ids=[r["call_id"] for r in receipts if r["tool_status"] != "SUCCESS"],
                              evidence=[n["reference"] for n in graph["nodes"] if n["type"] == "evidence"],
                              raw_receipt_ids=[r["call_id"] for r in receipts],
                              action_log=actions, next_step="核对关键缺口、条款上下文及查询权限后重新审核。")
        return {"version": VERSION, "prompt_version": PROMPT_VERSION, "mode": self.model.mode,
                "strategy": strategy, "task": task, "budget": asdict(self.budget), "graph": graph,
                "data_version": "synthetic-2026-11-10-v1",
                "history": history, "answer": answer, "scorecard": scorecard(graph, answer, actions),
                "action_log": actions, "tool_receipts": receipts, "model_calls": calls, "proposals": proposals,
                "escalation": escalation,
                "usage": {"rounds": rounds, "tool_calls": len(receipts), "model_calls": len(calls),
                          "model_cost_usd": cost if known_cost else None,
                          "observed_model_cost_usd": cost,
                          "tool_cost_units": sum(r.get("cost_units", 0) for r in receipts),
                          "elapsed_ms": round((monotonic()-start)*1000, 2)}}
