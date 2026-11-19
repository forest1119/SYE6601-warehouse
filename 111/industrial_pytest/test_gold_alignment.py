import json
from pathlib import Path

import pytest


TEST_ROOT = Path(__file__).resolve().parent
GOLD_ROOT = TEST_ROOT / "gold"

GOLD_FILES = [
    "工业_逐命题标准答案.json",
    "保险_逐命题标准答案.json",
]

VALID_STATUSES = {
    "SUPPORT",
    "REFUTE",
    "UNKNOWN",
    "CONFLICT",
    "MISSING_RULE",
}


@pytest.fixture(scope="session")
def gold_documents():
    documents = {}

    for filename in GOLD_FILES:
        path = GOLD_ROOT / filename

        assert path.is_file(), f"找不到标准答案文件：{path}"

        documents[filename] = json.loads(
            path.read_text(encoding="utf-8-sig")
        )

    return documents


@pytest.fixture(scope="session")
def gold_by_run_id(gold_documents):
    index = {}

    for filename, document in gold_documents.items():
        for run in document["runs"]:
            run_id = run["run_id"]

            assert run_id not in index, (
                f"标准答案存在重复run_id：{run_id}，"
                f"请检查文件：{filename}"
            )

            index[run_id] = run

    return index


@pytest.mark.parametrize("filename", GOLD_FILES)
def test_gold_file_structure(filename, gold_documents):
    """检查两份标准答案的基本结构和内部引用。"""
    document = gold_documents[filename]

    assert document["schema"] == "gold.v1"

    runs = document["runs"]

    assert len(runs) == 60, (
        f"{filename}应有60条，实际为{len(runs)}条"
    )

    case_ids = [run["case_id"] for run in runs]
    assert len(case_ids) == len(set(case_ids)), "case_id重复"

    for run in runs:
        claims = run["claims"]
        assert claims, f"{run['case_id']}没有命题标注"

        claim_ids = {
            claim["gold_claim_id"]
            for claim in claims
        }

        assert len(claim_ids) == len(claims), (
            f"{run['case_id']}命题ID重复"
        )

        for claim in claims:
            span = claim["answer_span"]

            assert span and span in run["ai_answer"], (
                f"{run['case_id']} / "
                f"{claim['gold_claim_id']}："
                "标注片段不在回答原文中"
            )

            status = claim["gold_status"]
            assert status in VALID_STATUSES

            expected_four_state = (
                "UNKNOWN"
                if status == "MISSING_RULE"
                else status
            )

            assert (
                claim["gold_status_four_state"]
                == expected_four_state
            ), "四态映射不一致"

        for gap in run["gaps"]:
            assert set(gap["affects_claims"]) <= claim_ids, (
                f"{run['case_id']} / "
                f"{gap['gold_gap_id']}引用不存在的命题"
            )


def read_json_pointer(document, pointer):
    """按JSON Pointer读取原始日志中的字段。"""
    assert pointer.startswith("/"), (
        f"无效JSON Pointer：{pointer}"
    )

    value = document

    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")

        if isinstance(value, list):
            value = value[int(token)]
        else:
            value = value[token]

    return value


def test_case_matches_gold(case, gold_by_run_id):
    """
    使用现有conftest.py中的case，
    检查实际测试日志与标准答案是否对应。
    """
    run_id = case["run_id"]

    assert run_id in gold_by_run_id, (
        f"没有找到对应标准答案：{run_id}"
    )

    gold = gold_by_run_id[run_id]

    for field in ("case_id", "user_question", "ai_answer"):
        assert case[field] == gold[field], (
            f"{run_id}的{field}与标准答案不一致，"
            "请检查是否使用了不同版本的数据集"
        )

    for claim in gold["claims"]:
        assert claim["answer_span"] in case["ai_answer"]

        for evidence in claim.get("evidence_values", []):
            pointer = evidence["json_pointer"]

            try:
                actual_value = read_json_pointer(
                    case,
                    pointer,
                )
            except (KeyError, IndexError, TypeError, ValueError):
                pytest.fail(
                    f"{run_id} / "
                    f"{claim['gold_claim_id']}："
                    f"原始日志中找不到字段 {pointer}"
                )

            assert actual_value == evidence["value"], (
                f"{run_id} / "
                f"{claim['gold_claim_id']}："
                f"字段 {pointer} 与标准答案依据不一致"
            )