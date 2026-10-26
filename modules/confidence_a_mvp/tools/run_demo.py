"""One command: tests then produce fresh outputs, without editing input fixtures."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from confidence_a import score_snapshot, evaluate_runs


def main():
    result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT)
    if result.returncode:
        return result.returncode
    out = ROOT / "outputs"
    out.mkdir(exist_ok=True)
    for source in sorted((ROOT / "examples").glob("*.snapshot.json")):
        card = score_snapshot(json.loads(source.read_text(encoding="utf-8")))
        (out / source.name.replace("snapshot", "scorecard")).write_text(
            json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{source.stem}: score={card['score']}, raw={card['raw_score']}, gate={card['gate_passed']}")
    report = evaluate_runs(json.loads((ROOT / "examples/runs.demo.json").read_text(encoding="utf-8")))
    (out / "metrics.demo.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Demo only; outputs written to:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
