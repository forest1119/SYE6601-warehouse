import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from graph_checks import check_graph_bundle
from trace_support import validate_case, check_prediction


def test_dataset_inventory(dataset, pytestconfig):
    assert len(dataset) == pytestconfig.getoption("--expected-count")

    case_ids = [case["case_id"] for case in dataset]
    run_ids = [case["run_id"] for case in dataset]

    assert len(set(case_ids)) == len(case_ids), "case_id重复"
    assert len(set(run_ids)) == len(run_ids), "run_id重复"

    # 工业、保险分别检查连续编号。
    prefixes = {case_id.split("-")[0] for case_id in case_ids}

    for prefix in prefixes:
        actual = sorted(
            case_id
            for case_id in case_ids
            if case_id.startswith(prefix + "-")
        )

        expected = [
            f"{prefix}-{number:03d}"
            for number in range(1, len(actual) + 1)
        ]

        assert actual == expected, f"{prefix}案例编号不连续"


def test_case_structure(case):
    validate_case(case)


@pytest.mark.interface
def test_interface(case, evaluator, pytestconfig):
    validate_case(case)

    graph_mode = pytestconfig.getoption("--graph-contract")

    expected_map = pytestconfig._trace_expected
    expected = (
        expected_map[case["run_id"]]
        if expected_map is not None
        else None
    )

    dataset_path = Path(pytestconfig.getoption("--dataset"))
    dataset_hash = hashlib.sha256(
        dataset_path.read_bytes()
    ).hexdigest()

    record = {
        "run_id": case["run_id"],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": dataset_hash,
        "adapter": pytestconfig.getoption("--adapter"),
        "check_scope": (
            "graph_contract"
            if graph_mode
            else "prediction_comparison"
            if expected_map is not None
            else "interface_smoke_only"
        ),
    }

    result = None
    start = time.monotonic()

    try:
        # 使用副本，防止适配器修改原始案例。
        case_copy = json.loads(json.dumps(case))

        if graph_mode:
            context = {
                "data_version": dataset_hash,
            }

            result = evaluator(case_copy, context)

        else:
            # 保留上一版本的单参数接口方式。
            result = evaluator(case_copy)

        check_prediction(result, expected)

        if graph_mode:
            assert "graph_bundle" in result, "适配器没有返回graph_bundle"

            bundle = result["graph_bundle"]

            record["graph_checks"] = check_graph_bundle(bundle)

            assert bundle["data_version"] == dataset_hash, (
                "输出记录的数据版本与本次输入不一致"
            )

            # 契约检查不是语义准确率。
            record["semantic_quality_not_evaluated"] = True

            if bundle["execution_kind"] != "real_model":
                record["not_a_real_model_experiment"] = True

        record["passed"] = True

    except Exception as error:
        record["passed"] = False
        record["error_type"] = type(error).__name__
        raise

    finally:
        record["elapsed_seconds"] = round(
            time.monotonic() - start,
            3,
        )
        record["result"] = result

        results_dir = Path(
            pytestconfig.getoption("--results-dir")
        )
        results_dir.mkdir(parents=True, exist_ok=True)

        result_path = results_dir / (
            f"{case['run_id']}_{time.time_ns()}.json"
        )

        result_path.write_text(
            json.dumps(
                record,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )