"""Run, replay and evaluate synthetic evidence harness cases."""

import argparse
import json
from pathlib import Path

from .cases import make_case
from .controller import Budget, Harness
from .evaluate import GOLD, assess, summarize
from .mock_model import FixtureModel
from .models import OpenRouter, Replay
from .report import markdown


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("simulated", "live"), default="simulated")
    parser.add_argument("--case", choices=tuple(GOLD), default="DYN-01")
    parser.add_argument("--strategy", choices=("dynamic", "fixed", "prompt", "configured", "no_expand"), default="dynamic")
    parser.add_argument("--suite", action="store_true", help="Compare strategies on the fixture matrix")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--replay", type=Path)
    parser.add_argument("--output", type=Path, default=Path("dynamic_evidence_artifacts"))
    args = parser.parse_args()
    if not 1 <= args.repeat <= 5:
        parser.error("--repeat must be between 1 and 5")
    if args.suite and args.mode == "live":
        parser.error("Run live cases individually to bound spend")
    if args.replay and (args.suite or args.mode != "simulated" or args.repeat != 1):
        parser.error("--replay accepts one recorded run at a time")
    recorded = json.loads(args.replay.read_text(encoding="utf-8")) if args.replay else None
    model = Replay(recorded["model_calls"]) if recorded else OpenRouter.from_env() if args.mode == "live" else FixtureModel()
    cases = tuple(GOLD) if args.suite else (recorded["task"]["task_id"] if recorded else args.case,)
    strategies = ("dynamic", "fixed", "prompt", "configured", "no_expand") if args.suite else (recorded["strategy"] if recorded else args.strategy,)
    rows = []
    for case in cases:
        for strategy in strategies:
            for _ in range(args.repeat):
                task, tool = make_case(case)
                if recorded:
                    task = recorded["task"]
                harness = Harness(model, tool, budget=Budget(**recorded["budget"]) if recorded else None)
                bundle = harness.run(task, strategy=strategy)
                entry = assess(bundle)
                name = f"{case}-{strategy}-{model.mode}-{entry['run_id']}"
                dump(args.output / f"{name}.json", bundle)
                (args.output / f"{name}.md").write_text(markdown(bundle), encoding="utf-8")
                rows.append(entry)
                print(case, strategy, entry["actual"], entry["stop_reason"], bundle["usage"])
    groups = {f"{strategy}/{origin}": summarize([r for r in rows if r["strategy"] == strategy and r["fault_origin"] == origin])
              for strategy, origin in sorted({(r["strategy"], r["fault_origin"]) for r in rows})}
    dump(args.output / f"summary-{model.mode}-{rows[0]['run_id']}.json", {"rows": rows, "groups": groups})


if __name__ == "__main__":
    main()
