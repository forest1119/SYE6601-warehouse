import json
import time
from pathlib import Path

import pytest

from test_evidence_project_rule import evidence_engine


TEST_ROOT = Path(__file__).resolve().parent


# 显式对齐：一条标准答案可以对应工程拆出的多个命题。
# 按内容匹配，不依赖CLM编号。
ALIGNMENTS = [
    {
        "actual_text": "检验结果为合格",
        "gold_span": "检验结果为合格",
    },
    {
        "actual_text": "证书有效期至2027年5月",
        "gold_span": "证书有效期至2027年5月",
    },
    {
        "actual_text": "今天吊装18吨设备没有问题",
        "gold_span": "今天吊装18吨设备没有问题，可以正常作业",
    },
    {
        "actual_text": "可以正常作业",
        "gold_span": "今天吊装18吨设备没有问题，可以正常作业",
    },
]


def normalize_text(text):
    """只忽略空白和句末标点，不做模糊语义匹配。"""
    return "".join(text.split()).rstrip("。；;！!")


def test_ind053_semantics(case, evidence_engine, pytestconfig):
    if case["case_id"] != "IND-053":
        pytest.skip("本轮先验证IND-053的显式语义对齐")

    gold_path = (
        TEST_ROOT
        / "gold"
        / "工业_逐命题标准答案.json"
    )

    document = json.loads(
        gold_path.read_text(encoding="utf-8-sig")
    )

    gold_runs = [
        run
        for run in document["runs"]
        if run["run_id"] == case["run_id"]
    ]

    assert len(gold_runs) == 1, "标准答案缺失或run_id重复"

    gold = gold_runs[0]

    assert gold["case_id"] == case["case_id"]
    assert gold["ai_answer"] == case["ai_answer"], (
        "实际日志与标准答案版本不一致"
    )

    settings, normalize_record, analyze_run, NullLLM = (
        evidence_engine
    )

    copied_case = json.loads(
        json.dumps(case, ensure_ascii=False)
    )

    artifact = analyze_run(
        normalize_record(copied_case),
        settings,
        llm=NullLLM("pytest强制规则模式"),
        validate=True,
    )

    assert artifact.schema_errors == [], (
        f"工程结构错误：{artifact.schema_errors}"
    )

    payload = artifact.to_dict()

    assert payload["graph"]["run_id"] == case["run_id"]
    assert payload["graph"]["case_id"] == case["case_id"]

    actual_claims = [
        node
        for node in payload["graph"]["nodes"]
        if node["type"] == "claim"
    ]

    checks = []
    failures = []

    for alignment in ALIGNMENTS:
        gold_matches = [
            claim
            for claim in gold["claims"]
            if claim["answer_span"] == alignment["gold_span"]
        ]

        assert len(gold_matches) == 1, (
            "标准答案命题缺失或不唯一："
            f"{alignment['gold_span']}"
        )

        expected_claim = gold_matches[0]
        expected_status = expected_claim["gold_status"]

        actual_matches = [
            claim
            for claim in actual_claims
            if normalize_text(claim["content"])
            == normalize_text(alignment["actual_text"])
        ]

        check = {
            "actual_text": alignment["actual_text"],
            "gold_claim_id": expected_claim["gold_claim_id"],
            "expected_status": expected_status,
            "rationale": expected_claim["rationale"],
        }

        if len(actual_matches) != 1:
            check["result"] = "ALIGNMENT_FAILED"
            check["candidate_count"] = len(actual_matches)

            failures.append(
                "命题对齐失败："
                f"{alignment['actual_text']}，"
                f"找到{len(actual_matches)}个匹配项"
            )
        else:
            actual = actual_matches[0]
            actual_status = actual.get("evidence_status")

            check["actual_claim_id"] = actual["id"]
            check["actual_status"] = actual_status

            if actual_status == expected_status:
                check["result"] = "MATCH"
            else:
                check["result"] = "STATUS_MISMATCH"

                failures.append(
                    f"{alignment['actual_text']}："
                    f"预期{expected_status}，"
                    f"实际{actual_status}"
                )

        checks.append(check)

    results_dir = (
        Path(pytestconfig.getoption("--results-dir"))
        / "gold_semantics"
    )
    results_dir.mkdir(parents=True, exist_ok=True)

    report_path = results_dir / (
        f"{case['run_id']}_{time.time_ns()}.json"
    )

    report = {
        "case_id": case["case_id"],
        "run_id": case["run_id"],
        "evaluation_kind": "development_semantic_regression",
        "model_called": False,
        "formal_acceptance": False,
        "gold_version": document.get("gold_version"),
        "gold_review_status": gold.get("review_status"),
        "passed": not failures,
        "checks": checks,
        "failures": failures,
        "output": payload,
    }

    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    assert not failures, (
        "\n"
        + "\n".join(failures)
        + f"\n详细报告：{report_path}"
    )