"""
证据链组 GraphProposal 的静态检查。

检查范围：
任务对应、ID、节点引用、状态字段、来源定位和引用原文。

不判断图是否语义正确。
不将提案当作已审核快照。
不代表真实模型或Loop已经运行。
"""

import json
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent
PROPOSAL_PATH = ROOT / "data" / "IND-001_GraphProposal.json"

# 两类状态分别检查，不能混用。
REVIEW_STATES = {
    "proposed",
    "accepted",
    "rejected",
    "unresolved",
}

EVIDENCE_STATES = {
    "SUPPORT",
    "REFUTE",
    "UNKNOWN",
    "CONFLICT",
}


@pytest.fixture(scope="module")
def proposal():
    if not PROPOSAL_PATH.is_file():
        pytest.fail(
            "找不到图提案文件，请将IND-001_GraphProposal.json"
            "放到industrial_pytest/data文件夹"
        )

    data = json.loads(
        PROPOSAL_PATH.read_text(encoding="utf-8-sig")
    )

    assert isinstance(data, dict), "图提案必须是JSON对象"

    for field in (
        "task",
        "graph_version",
        "nodes",
        "edges",
        "gaps",
        "checks",
        "proposal_status",
    ):
        assert field in data, f"图提案缺少字段：{field}"

    assert isinstance(data["task"], dict)
    assert isinstance(data["graph_version"], str)
    assert data["graph_version"].strip()

    for field in ("nodes", "edges", "gaps", "checks"):
        assert isinstance(data[field], list), (
            f"{field}必须是数组"
        )

    return data


@pytest.fixture(scope="module")
def source_log(proposal, dataset):
    """按实际task_id/run_id寻找来源日志，不硬编码标准答案。"""
    task = proposal["task"]

    matches = [
        case
        for case in dataset
        if case["case_id"] == task["task_id"]
        and case["run_id"] == task["run_id"]
    ]

    assert len(matches) == 1, (
        "提案必须唯一对应数据集中的一条日志；"
        "请核对数据版本、task_id和run_id"
    )

    return matches[0]


def records_by_id(source_log):
    return {
        event["id"]: event
        for event in source_log["trace"]
        if event["event"] == "tool_call"
    }


def resolve_locator(locator, source_log):
    """
    解析当前样例采用的自定义定位方式，例如：
    trace[c2].result.sensors[0]
    trace[c4].result.excerpt

    trace[c2]表示按事件id查找，不是数组下标。
    """
    assert isinstance(locator, str), "locator必须为字符串"

    match = re.fullmatch(
        r"trace\[([^\]]+)\](.*)",
        locator,
    )

    assert match is not None, (
        f"暂不支持的locator格式：{locator}"
    )

    event_id, remaining = match.groups()
    records = records_by_id(source_log)

    assert event_id in records, (
        f"locator引用的工具事件不存在：{event_id}"
    )

    value = records[event_id]

    while remaining:
        token = re.match(
            r"(?:\.([A-Za-z_][A-Za-z0-9_]*))"
            r"|(?:\[(\d+)\])",
            remaining,
        )

        assert token is not None, (
            f"无法解析locator剩余部分：{remaining}"
        )

        field_name, index_text = token.groups()

        if field_name is not None:
            assert isinstance(value, dict), (
                f"定位{field_name}时，上一级不是对象"
            )
            assert field_name in value, (
                f"locator引用的字段不存在：{field_name}"
            )

            value = value[field_name]

        else:
            index = int(index_text)

            assert isinstance(value, list), (
                "使用数组下标时，上一级不是数组"
            )
            assert index < len(value), (
                f"locator数组下标越界：{index}"
            )

            value = value[index]

        remaining = remaining[token.end():]

    return event_id, value


def assert_unique_ids(items, label):
    ids = []

    for item in items:
        assert isinstance(item, dict), (
            f"{label}中的元素必须是对象"
        )

        item_id = item.get("id")

        assert isinstance(item_id, str) and item_id.strip(), (
            f"{label}缺少非空id"
        )

        ids.append(item_id)

    assert len(ids) == len(set(ids)), (
        f"{label}存在重复id"
    )

    return set(ids)


# ---------------------------------------------------------
# 1. 图提案是否对应当前日志
# ---------------------------------------------------------

def test_proposal_task_binding(proposal, source_log):
    task = proposal["task"]

    assert task["task_id"] == source_log["case_id"]
    assert task["run_id"] == source_log["run_id"]
    assert task["question"] == source_log["user_question"], (
        "提案中的问题与来源日志不一致"
    )


# ---------------------------------------------------------
# 2. 节点、边、缺口、检查项编号是否唯一
# ---------------------------------------------------------

def test_proposal_unique_ids(proposal):
    assert proposal["nodes"], "提案没有任何节点"

    assert_unique_ids(proposal["nodes"], "nodes")
    assert_unique_ids(proposal["edges"], "edges")
    assert_unique_ids(proposal["gaps"], "gaps")

    check_ids = [
        item["check_id"]
        for item in proposal["checks"]
    ]

    assert all(
        isinstance(value, str) and value.strip()
        for value in check_ids
    ), "check_id必须为非空字符串"

    assert len(check_ids) == len(set(check_ids)), (
        "checks存在重复check_id"
    )


# ---------------------------------------------------------
# 3. 边与缺口引用的节点是否存在
# ---------------------------------------------------------

def test_proposal_node_references(proposal):
    nodes = {
        node["id"]: node
        for node in proposal["nodes"]
    }

    for edge in proposal["edges"]:
        assert edge["from"] in nodes, (
            f"{edge['id']}的from节点不存在"
        )

        assert edge["to"] in nodes, (
            f"{edge['id']}的to节点不存在"
        )

        assert isinstance(
            edge.get("type"), str
        ) and edge["type"].strip(), (
            f"{edge['id']}缺少关系类型"
        )

    for gap in proposal["gaps"]:
        affected = gap.get("affected_claims")

        assert isinstance(affected, list) and affected, (
            f"{gap['id']}没有affected_claims"
        )

        for claim_id in affected:
            assert claim_id in nodes, (
                f"{gap['id']}引用的主张不存在：{claim_id}"
            )

            assert nodes[claim_id]["type"] == "claim", (
                f"{gap['id']}引用的对象不是claim：{claim_id}"
            )


# ---------------------------------------------------------
# 4. 审核状态与证据状态是否区分
# ---------------------------------------------------------

def test_proposal_state_fields(proposal):
    assert proposal["proposal_status"] in REVIEW_STATES, (
        "proposal_status不是有效审核状态"
    )

    for node in proposal["nodes"]:
        assert isinstance(
            node.get("content"), str
        ) and node["content"].strip(), (
            f"{node['id']}缺少content"
        )

        # 样例不是每个fact/rule/evidence节点都有审核状态，
        # 所以仅在字段存在时检查，不自行补造。
        if "review_status" in node:
            assert node["review_status"] in REVIEW_STATES, (
                f"{node['id']}混用了审核状态"
            )

        if "evidence_status" in node:
            assert node["evidence_status"] in EVIDENCE_STATES, (
                f"{node['id']}混用了命题证据状态"
            )

    for edge in proposal["edges"]:
        if "review_status" in edge:
            assert edge["review_status"] in REVIEW_STATES


# ---------------------------------------------------------
# 5. 证据定位、检查项是否能找到实际工具调用
# ---------------------------------------------------------

def test_proposal_source_locations(proposal, source_log):
    records = records_by_id(source_log)

    evidence_nodes = [
        node
        for node in proposal["nodes"]
        if node["type"] == "evidence"
    ]

    assert evidence_nodes, "提案没有证据节点"

    for node in evidence_nodes:
        record_id = node.get("record_id")

        assert record_id in records, (
            f"{node['id']}的record_id不存在"
        )

        located_id, _ = resolve_locator(
            node["locator"],
            source_log,
        )

        assert located_id == record_id, (
            f"{node['id']}的locator与record_id不一致"
        )

        assert isinstance(
            node.get("source_id"), str
        ) and node["source_id"].strip(), (
            f"{node['id']}缺少source_id"
        )

    for check in proposal["checks"]:
        assert check["source_record"] in records, (
            f"{check['check_id']}引用的工具事件不存在"
        )

    # 这里只证明位置存在；
    # source_id与实际来源的业务映射仍需确认正式协议。


# ---------------------------------------------------------
# 6. 提案引用的手册原文是否忠于来源
# ---------------------------------------------------------

def test_proposal_excerpts(proposal, source_log):
    for node in proposal["nodes"]:
        if "excerpt" not in node:
            continue

        quote = node["excerpt"]

        assert isinstance(quote, str) and quote.strip(), (
            f"{node['id']}的excerpt为空"
        )

        _, located_value = resolve_locator(
            node["locator"],
            source_log,
        )

        assert isinstance(located_value, str), (
            f"{node['id']}的excerpt没有定位到文本字段"
        )

        assert quote in located_value, (
            f"{node['id']}的引用原文与日志不一致"
        )