"""
测试侧的图结构对接草案。

真实工程的字段由证据链组提供，再通过适配器映射。
不能为了通过测试而补造图、工具回执或模型调用。
"""


def check_graph_bundle(bundle):
    assert isinstance(bundle, dict), "graph_bundle必须是对象"

    execution_kind = bundle.get("execution_kind")
    assert execution_kind in {
        "real_model", "replay", "mock"
    }, "必须如实注明real_model、replay或mock"

    # 保存实际运行配置，便于后续复核。
    for field in (
        "method",
        "model_manifest",
        "prompt_version",
        "config",
        "data_version",
    ):
        assert field in bundle, f"缺少运行记录：{field}"

    assert isinstance(
        bundle["model_manifest"], dict
    ), "model_manifest必须是对象"

    assert isinstance(bundle["config"], dict), "config必须是对象"

    # 工具回执与可定位的原文。
    receipts = bundle.get("tool_receipts")
    assert isinstance(receipts, list), "tool_receipts必须是数组"

    receipt_map = {}

    for receipt in receipts:
        receipt_id = receipt["id"]

        assert receipt_id not in receipt_map, "工具回执ID重复"
        assert isinstance(
            receipt.get("source_text"), str
        ), "工具回执需要保留source_text"

        receipt_map[receipt_id] = receipt["source_text"]

    # 按实际发生顺序保存图快照。
    snapshots = bundle.get("snapshots")
    assert isinstance(snapshots, list) and snapshots, "缺少图快照"

    versions = []

    for snapshot in snapshots:
        version = snapshot.get("version")

        assert isinstance(version, str) and version, "快照版本不能为空"
        assert version not in versions, "快照版本重复"

        versions.append(version)

        nodes = snapshot.get("nodes")
        edges = snapshot.get("edges")

        assert isinstance(nodes, list), "nodes必须是数组"
        assert isinstance(edges, list), "edges必须是数组"

        node_status = {}

        for node in nodes:
            node_id = node["id"]

            assert node_id not in node_status, "节点ID重复"
            assert isinstance(
                node.get("text"), str
            ) and node["text"].strip(), "节点缺少文本"

            status = node.get("review_status")

            assert status in {
                "candidate", "accepted", "rejected"
            }, "节点必须区分候选、已接纳、已拒绝状态"

            node_status[node_id] = status

            for reference in node.get("evidence", []):
                receipt_id = reference["receipt_id"]
                quote = reference.get("quote")

                assert receipt_id in receipt_map, "引用的回执不存在"
                assert isinstance(quote, str) and quote, "引用原文为空"
                assert quote in receipt_map[receipt_id], "引用无法在原文中定位"

        for edge in edges:
            source = edge["source"]
            target = edge["target"]

            assert source in node_status, "边的起点不存在"
            assert target in node_status, "边的终点不存在"

            assert isinstance(
                edge.get("relation"), str
            ) and edge["relation"], "关系类型为空"

            status = edge.get("review_status")

            assert status in {
                "candidate", "accepted", "rejected"
            }, "边缺少审核状态"

            if status == "accepted":
                assert node_status[source] == "accepted", (
                    "已接纳的边不能连接尚未接纳的起点"
                )
                assert node_status[target] == "accepted", (
                    "已接纳的边不能连接尚未接纳的终点"
                )

    final_version = bundle.get("final_snapshot_version")

    assert final_version == versions[-1], "最终版本不是最后一个快照"

    # 包括升级、失败等情况，也应有对应版本的输出。
    for field in ("answer", "scorecard"):
        output = bundle.get(field)

        assert isinstance(output, dict), f"缺少{field}"
        assert output.get("snapshot_version") == final_version, (
            f"{field}与最终图快照版本不一致"
        )

    assert isinstance(
        bundle.get("actions"), list
    ), "需要保留实际动作记录"

    if execution_kind == "real_model":
        assert bundle["model_manifest"].get("model"), "缺少实际模型名称"

        calls = bundle.get("model_calls")

        assert isinstance(calls, list) and calls, "缺少实际模型调用记录"

        for call in calls:
            for field in ("call_id", "input", "output"):
                assert field in call, f"模型调用缺少{field}"

    return {
        "snapshot_count": len(snapshots),
        "receipt_count": len(receipts),
        "execution_kind": execution_kind,
    }