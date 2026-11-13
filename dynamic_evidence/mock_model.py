"""Deterministic interface fixture. Never report its results as model performance."""

import json
import re

class FixtureModel:
    mode = "simulated"

    def __call__(self, stage, messages, timeout):
        data = json.loads(messages[-1]["content"])
        if stage == "build":
            claims = [{"kind": "eligibility", "text": data["question"]}]
            if data["candidate_answer"] and "$" in data["candidate_answer"]:
                claims.append({"kind": "amount", "text": data["candidate_answer"]})
            conditions = []
            for record in data["records"]:
                clause = record["text"]
                kind, value = "unexpanded", None
                duration = re.search(r"at least (\d+) minutes", clause)
                deadline = re.search(r"(?:must be submitted within|ticket within|no later than) (\d+) hours", clause)
                if duration:
                    kind, value = "duration_min", int(duration[1])
                elif deadline:
                    kind, value = "ticket_deadline_hours", int(deadline[1])
                conditions.append({"record_id": record["record_id"], "kind": kind, "value": value,
                                   "excerpt": clause})
            result = {"claims": claims, "conditions": conditions}
        elif stage == "prompt":
            # A wiring fixture for this baseline; it is deliberately excluded from live comparisons.
            result = {"recommendation": "undetermined", "reason": "Simulated prompt adapter",
                      "evidence_ids": []}
        else:
            result = {"verdict": "accepted", "reason": "Simulated interface fixture"}
        return {"model": "fixture", "usage": {"cost": 0}, "raw_output": json.dumps(result)}
