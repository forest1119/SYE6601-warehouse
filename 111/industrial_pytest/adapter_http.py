"""EXAMPLE ONLY: confirm request/response mapping with your team's API owner."""
import json
import os
from urllib.request import Request, urlopen


def build_payload(case):
    # Current example sends the full trace directly. Change ONLY after API contract is known.
    # ai_answer is the recorded answer to be evaluated, NOT a reference answer to imitate.
    return case


def normalize_response(raw):
    # Example contract assumes server returns {"prediction": {...}}.
    # Map actual server fields here. No correctness labels are fabricated.
    return {'prediction': raw['prediction'], 'raw_response': raw}


def evaluate(case):
    endpoint = os.environ.get('TRACE_EVAL_URL')
    if not endpoint:
        raise ValueError('Set TRACE_EVAL_URL to a confirmed evaluation endpoint')
    headers = {'Content-Type': 'application/json'}
    token = os.environ.get('TRACE_EVAL_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = Request(endpoint, data=json.dumps(build_payload(case)).encode('utf-8'), headers=headers, method='POST')
    with urlopen(req, timeout=float(os.environ.get('TRACE_EVAL_TIMEOUT', '120'))) as response:
        raw = json.load(response)
    return normalize_response(raw)
