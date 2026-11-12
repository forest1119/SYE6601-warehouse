"""Synthetic tool data only. Gold labels live in the evaluation module."""

from datetime import timedelta

from .matrix import DEADLINE_TEMPLATES, MATRIX
from .tools import CONTRACT, INCIDENT, MAINTENANCE, POLICY, TICKET, SyntheticTools
from .tools import moment

DEADLINE_TEXT = "A ticket must be submitted within 24 hours after the incident."
POLICY_TEXT = "Compensation requires an outage lasting at least 60 minutes."


def make_case(name="DYN-01", question=None, candidate_answer=None):
    ids = ("DYN-01", "NO-TICKET", "LATE-TICKET", "CONTRACT-403", "TICKET-403",
           "MAINTENANCE", "OLD-CONTRACT", "CONFLICT", "REFERRAL", "AMOUNT", "BOUNDARY",
           "SHORT-OUTAGE", "EMPTY-CONTRACT", "NEGATED", "MISSING-TICKET")
    if name not in ids and name not in MATRIX:
        raise ValueError(f"Unknown synthetic case: {name}")
    task = {"task_id": name, "question": question or "Is this outage eligible for compensation?",
            "customer_id": "C-DEMO", "incident_id": "I-DEMO", "event_time": "2026-10-01T00:00:00Z",
            "candidate_answer": candidate_answer, "scenarios": {}}
    if name == "AMOUNT" and candidate_answer is None:
        task["candidate_answer"] = "Compensation is $500."
    for case_id, source, scenario in (
        ("CONTRACT-403", CONTRACT, "forbidden"), ("TICKET-403", TICKET, "forbidden"),
        ("OLD-CONTRACT", CONTRACT, "old_version"), ("CONFLICT", CONTRACT, "conflicting_materials")
    ):
        if name == case_id:
            task["scenarios"][source] = scenario

    def row(source, evidence_id, statement, **fields):
        return {"source_type": source, "evidence_id": evidence_id, "statement": statement,
                "customer_id": task["customer_id"], "incident_id": task["incident_id"],
                "version": "v1", "effective_from": "2026-01-01T00:00:00Z",
                "effective_to": "2026-12-31T23:59:59Z", "citation": f"synthetic:{evidence_id}", **fields}

    clauses = [row(CONTRACT, "C-THRESHOLD", "The incident must last at least 90 minutes.")]
    if name not in ("NO-TICKET", "OLD-CONTRACT", "CONFLICT", "EMPTY-CONTRACT"):
        if name == "REFERRAL":
            clauses.append(row(CONTRACT, "C-REFERRAL", "Eligibility is subject to the unpublished Schedule Z."))
        elif name == "NEGATED":
            clauses.append(row(CONTRACT, "C-NEGATION", "A ticket is not required within 24 hours after the incident."))
        else:
            clauses.append(row(CONTRACT, "C-DEADLINE", DEADLINE_TEXT))
    ticket_time = {"LATE-TICKET": "2026-10-02T00:00:01Z",
                   "BOUNDARY": "2026-10-02T00:00:00Z"}.get(name, "2026-10-01T12:00:00Z")
    records = {
        POLICY: [row(POLICY, "P-THRESHOLD", POLICY_TEXT)],
        INCIDENT: [row(INCIDENT, "I-DURATION", "Verified outage duration.",
                       duration_minutes=80 if name == "SHORT-OUTAGE" else 120)],
        CONTRACT: [] if name == "EMPTY-CONTRACT" else clauses,
        MAINTENANCE: [row(MAINTENANCE, "M-01", "Applicable planned maintenance.", excluded=True)]
        if name == "MAINTENANCE" else [],
        TICKET: [] if name == "MISSING-TICKET" else [
            row(TICKET, "T-01", "Verified ticket submission.", submitted_at=ticket_time)],
    }
    if name in MATRIX:
        template, hours, boundary, duration = MATRIX[name]
        records[CONTRACT][1]["statement"] = DEADLINE_TEMPLATES[template].format(hours=hours)
        records[INCIDENT][0]["duration_minutes"] = duration
        if boundary == "missing":
            records[TICKET] = []
        else:
            seconds = {"early": hours*3600-1, "exact": hours*3600, "late": hours*3600+1}[boundary]
            records[TICKET][0]["submitted_at"] = (moment(task["event_time"]) + timedelta(seconds=seconds)).isoformat()
    return task, SyntheticTools(records)
