"""07A scorecard and plain-language export from the same frozen versions."""

IDENTITY = ("task_id", "run_id", "graph_version", "answer_version")
LABELS = {"eligible": "建议补偿", "ineligible": "不建议补偿", "undetermined": "暂无法确定"}
SCORE_VERSION = "dynamic-score-1.0"


def scorecard(graph, answer, action_log):
    if any(graph[key] != answer[key] for key in IDENTITY):
        raise ValueError("Answer and graph versions do not match")
    gaps = graph["gaps"]
    blockers = [g for g in gaps if g["critical"] or g["must_verify"]]
    claims = [n for n in graph["nodes"] if n["type"] == "claim"]
    conditions = [n for n in graph["nodes"] if n["id"].startswith("condition:")]
    evidence = [n["reference"] for n in graph["nodes"] if n["type"] == "evidence"]
    coverage = graph["coverage"]
    parts = {
        "基础必查": [sum(c["completed"] for c in coverage), len(coverage)],
        "已映射主张": [sum(c["review_status"] == "accepted" for c in claims), len(claims)],
        "条件已判定": [sum(n["state"] in ("SUPPORT", "REFUTE") for n in conditions), len(conditions)],
        "关系审核通过": [sum(c["review_status"] == "accepted" for c in graph["checks"]), len(graph["checks"])],
    }
    sufficient = bool(not blockers and graph["recommendation"] != "undetermined")
    level = ("附保留说明" if gaps else "已建模范围内证据充分") if sufficient else "证据不足"
    return {**{key: graph[key] for key in IDENTITY}, "scoring_version": SCORE_VERSION,
            "recommendation": graph["recommendation"], "workflow_status": graph["workflow_status"],
            "level": level, "parts": parts, "blockers": blockers, "gaps": gaps,
            "review_priority": sorted(gaps, key=lambda g: (not g["must_verify"], not g["critical"])),
            "claims": claims, "conditions": conditions, "evidence": evidence,
            "action_log": action_log, "changes": graph["changes"],
            "scope_declaration": graph["scope_declaration"], "stop_reason": graph["stop_reason"]}


def markdown(bundle):
    graph, card, answer = (bundle[k] for k in ("graph", "scorecard", "answer"))
    if any(any(item[k] != graph[k] for k in IDENTITY) for item in (card, answer)):
        raise ValueError("Bundle versions differ")
    lines = ["# 证据成绩单", "", bundle["task"]["question"], "", answer["text"], "", card["level"],
             "", " · ".join(f"{k}={card[k]}" for k in IDENTITY), "",
             f"模式 {bundle['mode']} · 终止 {card['stop_reason']}", "", card["scope_declaration"],
             "", "## 分项", *[f"- {k} {v[0]}/{v[1]}" for k, v in card["parts"].items()],
             "", "## 优先复核", *[f"- {g['gap_type']} · {g['reason']}" for g in card["review_priority"]],
             "", "## 主张与条件", *[f"- {n['id']} · {n.get('state', '')} · {n.get('text', n.get('value', ''))}"
                                       for n in card["claims"] + card["conditions"]],
             "", "## 来源", *[f"- {e['record_id']} · {e['locator']} · {e['excerpt']}" for e in card["evidence"]],
             "", "## 结构变化", *[f"- v{s['graph_version']} · {c['kind']} · {c['object_id']}"
                                     for s in bundle["history"] for c in s["changes"]]]
    return "\n".join(lines) + "\n"
