"""Run the evidence harness with the team's merged Loop B provider."""

import argparse
from pathlib import Path

from loop_b_unified import create_provider, make_review_packet

from .__main__ import dump
from .cases import make_case
from .controller import Harness
from .mock_model import FixtureModel
from .models import OpenRouter
from .report import markdown
from .tools import TICKET


def run_unified(model, *, ticket_forbidden=False, bundle_id="bundle-01"):
    task, _ = make_case("DYN-01")
    provider = create_provider(bundle_id, faults={TICKET: "forbidden"} if ticket_forbidden else {})
    bundle = Harness(model, provider).run(task)
    bundle["tool_provider"] = "loop_b_unified"
    bundle["tool_bundle_id"] = bundle_id
    if bundle["escalation"]:
        bundle["review_packet"] = make_review_packet(
            bundle["graph"], bundle["tool_receipts"], bundle["action_log"],
            attempted_rounds=bundle["usage"]["rounds"],
            total_tool_calls=bundle["usage"]["tool_calls"],
            questions=["请核实关键缺口、条款上下文和查询权限。"],
        )
    return bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--ticket-forbidden", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("dynamic_evidence_artifacts"))
    args = parser.parse_args()
    model = OpenRouter.from_env() if args.live else FixtureModel()
    bundle = run_unified(model, ticket_forbidden=args.ticket_forbidden)
    name = f"unified-{bundle['mode']}-{bundle['task']['run_id']}"
    dump(args.output / f"{name}.json", bundle)
    (args.output / f"{name}.md").write_text(markdown(bundle), encoding="utf-8")
    print(bundle["graph"]["recommendation"], bundle["graph"]["stop_reason"], bundle["usage"])


if __name__ == "__main__":
    main()
