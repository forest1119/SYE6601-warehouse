"""Dataset validation and adapter contract; no model or business-tool execution here."""
import json
import re
from datetime import datetime
from pathlib import Path

TOP = {'case_id', 'run_id', 'user_question', 'visible_context', 'trace', 'ai_answer'}
CALL = {'id', 'event', 'type', 'tool', 'arguments', 'result'}
NOTE = {'id', 'event', 'text'}
TYPES = {'basic_lookup', 'ops_monitoring', 'knowledge_base_search', 'database_query', 'document_lookup', 'external_api'}


def load_dataset(path):
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    def reject_constant(value):
        raise ValueError(f'Invalid JSON constant: {value}')
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'),
                      object_pairs_hook=unique_keys, parse_constant=reject_constant)
    if not isinstance(data, list) or not data:
        raise ValueError('Dataset must be a nonempty JSON array')
    return data


def validate_case(case):
    assert isinstance(case, dict) and set(case) == TOP, 'Exactly six top-level fields required'
    assert isinstance(case['case_id'], str) and re.fullmatch(r'(?:IND|INS)-\d{3}', case['case_id']), 'Invalid case_id'
    assert case['run_id'] == case['case_id'] + '-r1', 'Invalid run_id'
    for key in ('user_question', 'ai_answer'):
        assert isinstance(case[key], str) and case[key].strip(), f'{key} must be nonempty text'
    context = case['visible_context']
    assert isinstance(context, dict), 'visible_context must be an object'
    assert isinstance(context.get('received_at'), str), 'received_at required'
    dt = datetime.fromisoformat(context['received_at'])
    assert dt.utcoffset() is not None and dt.utcoffset().total_seconds() == 28800, 'received_at must use +08:00'
    assert isinstance(case['trace'], list) and case['trace'], 'trace must be a nonempty array'
    calls = notes = 0
    for e in case['trace']:
        assert isinstance(e, dict), 'trace event must be an object'
        if e.get('event') == 'tool_call':
            calls += 1
            assert set(e) == CALL and e['id'] == f'c{calls}', 'Invalid tool event fields or sequence'
            assert e['type'] in TYPES, 'Invalid tool type'
            assert isinstance(e['tool'], str) and e['tool'].strip(), 'Missing tool name'
            assert isinstance(e['arguments'], dict) and isinstance(e['result'], dict), 'arguments/result must be objects'
        elif e.get('event') == 'assistant_progress_note':
            notes += 1
            assert set(e) == NOTE and e['id'] == f's{notes}', 'Invalid note fields or sequence'
            assert isinstance(e['text'], str) and e['text'].strip(), 'Missing note text'
        else:
            raise AssertionError('Unsupported event kind')
    assert calls >= 1, 'At least one tool call required'
    # No semantic assertions: wrong ai_answer values are intentional dataset content.


def check_prediction(result, expected=None):
    """Adapter normalizes its own response to this local test contract."""
    assert isinstance(result, dict), 'Adapter must return a dict'
    assert isinstance(result.get('prediction'), dict) and result['prediction'], 'Nonempty prediction object required'
    assert 'raw_response' in result, 'Adapter must preserve raw_response'
    if expected is not None:
        assert isinstance(expected, dict) and expected, 'Expectation must be a nonempty dict'
        for key, value in expected.items():
            assert key in result['prediction'], f'Missing expected prediction key: {key}'
            assert type(result['prediction'][key]) is type(value) and result['prediction'][key] == value, f'Prediction mismatch for {key}'
