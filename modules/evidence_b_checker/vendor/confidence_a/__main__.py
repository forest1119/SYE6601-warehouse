import argparse
import json
import sys
from pathlib import Path

from .contracts import ContractError, exported_schemas
from .metrics import evaluate_runs
from .scoring import score_snapshot


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="07A 证据评分 MVP")
    subs = parser.add_subparsers(dest="command", required=True)
    score = subs.add_parser("score")
    score.add_argument("input")
    score.add_argument("--policy")
    score.add_argument("--output", required=True)
    metrics = subs.add_parser("metrics")
    metrics.add_argument("input")
    metrics.add_argument("--output", required=True)
    schemas = subs.add_parser("schemas")
    schemas.add_argument("--output-dir", default="schemas")
    args = parser.parse_args()
    try:
        if args.command == "schemas":
            for name, schema in exported_schemas().items():
                write_json(Path(args.output_dir) / f"{name}.schema.json", schema)
            return 0
        source = Path(args.input).resolve()
        target = Path(args.output).resolve()
        if source == target or (args.command == "score" and args.policy and Path(args.policy).resolve() == target):
            raise ContractError("输出路径不能覆盖输入或策略文件")
        payload = read_json(source)
        result = (score_snapshot(payload, read_json(args.policy) if args.policy else None)
                  if args.command == "score" else evaluate_runs(payload))
        write_json(target, result)
        print(f"Written: {target}")
        return 0
    except (ContractError, ValueError, OSError) as error:
        print(f"Input error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
