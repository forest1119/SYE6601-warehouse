import json
import unittest
from pathlib import Path

from confidence_a.contracts import exported_schemas, validate, SCORECARD_SCHEMA
from confidence_a.scoring import score_snapshot

ROOT = Path(__file__).resolve().parents[1]


class ExportTests(unittest.TestCase):
    def test_exported_schemas_match_executable_contract(self):
        for name, schema in exported_schemas().items():
            self.assertEqual(json.loads((ROOT / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8")), schema)

    def test_saved_cards_match_current_logic_and_output_contract(self):
        for path in (ROOT / "examples").glob("*.snapshot.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            card = score_snapshot(data)
            validate(card, SCORECARD_SCHEMA)
            expected = json.loads(path.with_name(path.name.replace("snapshot", "scorecard")).read_text(encoding="utf-8"))
            self.assertEqual(card, expected)


if __name__ == "__main__":
    unittest.main()
