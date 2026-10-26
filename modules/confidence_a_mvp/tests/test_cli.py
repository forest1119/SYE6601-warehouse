import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "confidence_a", *map(str, args)], cwd=ROOT,
                              capture_output=True, text=True)

    def test_score_and_metrics_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            for command, source in (("score", "03_contract_unknown.snapshot.json"), ("metrics", "runs.demo.json")):
                target = Path(temp) / f"{command}.json"
                result = self.run_cli(command, ROOT / "examples" / source, "--output", target)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIsInstance(json.loads(target.read_text(encoding="utf-8")), dict)

    def test_invalid_input_does_not_write_score(self):
        with tempfile.TemporaryDirectory() as temp:
            source, target = Path(temp) / "bad.json", Path(temp) / "card.json"
            source.write_text('{}', encoding="utf-8")
            result = self.run_cli("score", source, "--output", target)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(target.exists())

    def test_cannot_overwrite_source(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "input.json"
            source.write_text('{}', encoding="utf-8")
            result = self.run_cli("score", source, "--output", source)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(source.read_text(encoding="utf-8"), '{}')


if __name__ == "__main__":
    unittest.main()
