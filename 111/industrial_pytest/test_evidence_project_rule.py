"""
批量调用证据链工程，检查实际规则模式输出。

使用现有conftest.py提供的60条case。
不调用模型，不修改数据，不把结构通过当作语义正确。
"""

import hashlib
import json
import sys
import time
from pathlib import Path

import pytest


TEST_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_ROOT.parent / "evidence_graph"


@pytest.fixture(scope="module")
def evidence_engine():
    pipeline_file = PROJECT_ROOT / "egraph" / "pipeline.py"

    assert pipeline_file.is_file(), (
        "找不到证据链工程。请确认evidence_graph与"
        "industrial_pytest是同级目录，且没有多套一层文件夹。"
    )

    sys.path.insert(0, str(PROJECT_ROOT))

    import config.settings as settings_module
    import egraph.pipeline as pipeline_module

    from egraph.loader import normalize_record
    from egraph.llm.client import NullLLM

    # 防止误导入项目中其他同名包。
    assert Path(settings_module.__file__).resolve().is_relative_to(
        PROJECT_ROOT.resolve()
    ), "导入了其他config包，请检查目录并重新启动测试进程"

    assert Path(pipeline_module.__file__).resolve().is_relative_to(
        PROJECT_ROOT.resolve()
    ), "导入了其他egraph包，请检查目录"

    settings = settings_module.load_settings(
        {
            "mode": "rule",
            "render": False,
        },
        env={},
    )

    return (
        settings,
        normalize_record,
        pipeline_module.analyze_run,
        NullLLM,
    )


def test_real_project_rule(case, evidence_engine, pytestconfig):
    settings, normalize_record, analyze_run, NullLLM = evidence_engine

    original = json.dumps(
        case,
        ensure_ascii=False,
        sort_keys=True,
    )

    record = {
        "case_id": case["case_id"],
        "run_id": case["run_id"],
        "execution_kind": "actual_project_rule_mode",
        "model_called": False,
        "semantic_accuracy_evaluated": False,
        "input_sha256": hashlib.sha256(
            original.encode("utf-8")
        ).hexdigest(),
    }

    payload = None
    started = time.monotonic()

    try:
        # 深复制，避免工程修改pytest中的原始案例。
        copied_case = json.loads(
            json.dumps(case, ensure_ascii=False)
        )

        artifact = analyze_run(
            normalize_record(copied_case),
            settings,
            llm=NullLLM("pytest强制规则模式"),
            validate=True,
        )

        payload = artifact.to_dict()

        assert artifact.schema_errors == [], (
            f"工程结构校验失败：{artifact.schema_errors}"
        )

        graph = payload["graph"]
        plan = payload["plan"]
        scorecard = payload["scorecard"]

        # 三份产出必须对应同一条输入日志。
        for output in (graph, plan, scorecard):
            assert output["case_id"] == case["case_id"]
            assert output["run_id"] == case["run_id"]

        nodes = graph["nodes"]

        node_ids = [node["id"] for node in nodes]
        gap_ids = [gap["id"] for gap in graph["gaps"]]
        edge_ids = [edge["id"] for edge in graph["edges"]]

        assert len(node_ids) == len(set(node_ids)), "节点ID重复"
        assert len(gap_ids) == len(set(gap_ids)), "缺口ID重复"
        assert len(edge_ids) == len(set(edge_ids)), "边ID重复"

        claim_ids = {
            node["id"]
            for node in nodes
            if node["type"] == "claim"
        }

        assert claim_ids, "没有抽取出任何主张"

        # 当前工程允许部分边指向graph.gaps中的缺口对象。
        valid_endpoints = set(node_ids) | set(gap_ids)

        for edge in graph["edges"]:
            assert edge["source"] in valid_endpoints, (
                f"边起点不存在：{edge}"
            )
            assert edge["target"] in valid_endpoints, (
                f"边终点不存在：{edge}"
            )

        # 当前工程record_id可能引用trace事件，
        # 也可能引用已抽取的图节点。
        valid_records = {
            event["id"]
            for event in case["trace"]
        } | set(node_ids)

        for node in nodes:
            reference = node.get("record_id")

            if reference is not None:
                assert reference in valid_records, (
                    f"{node['id']}引用了不存在的记录：{reference}"
                )

        # 缺口关联的主张必须真的存在。
        for gap in graph["gaps"]:
            missing = set(gap["affected_claims"]) - claim_ids

            assert not missing, (
                f"{gap['id']}引用了不存在的主张："
                f"{sorted(missing)}"
            )

        # 补证计划引用的缺口和主张必须存在。
        for action in plan["actions"]:
            assert set(action["gap_ids"]) <= set(gap_ids), (
                f"{action['id']}引用了不存在的缺口"
            )
            assert set(action["target_claims"]) <= claim_ids, (
                f"{action['id']}引用了不存在的主张"
            )

        # 成绩单必须评价图中实际存在的主张。
        for claim in scorecard["claims"]:
            assert claim["claim_id"] in claim_ids, (
                f"成绩单引用了不存在的主张：{claim['claim_id']}"
            )

        assert json.dumps(
            case,
            ensure_ascii=False,
            sort_keys=True,
        ) == original, "原始案例被修改"

        record["passed"] = True

    except Exception as error:
        record["passed"] = False
        record["error_type"] = type(error).__name__
        raise

    finally:
        # 成功或失败都保存实际输出，便于反馈和复现。
        record["elapsed_seconds"] = round(
            time.monotonic() - started,
            4,
        )
        record["output"] = payload

        results_dir = (
            Path(pytestconfig.getoption("--results-dir"))
            / "evidence_rule"
        )
        results_dir.mkdir(parents=True, exist_ok=True)

        result_file = results_dir / (
            f"{case['run_id']}_{time.time_ns()}.json"
        )

        result_file.write_text(
            json.dumps(
                record,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )