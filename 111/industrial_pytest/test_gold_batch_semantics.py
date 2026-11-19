"""工业离线规则输出的开发语义回归，保留待对齐项，不计算正式准确率。"""
import json
import time
from collections import Counter
from pathlib import Path

import pytest
from test_evidence_project_rule import evidence_engine

TEST_ROOT = Path(__file__).resolve().parent


def normalized(text):
    return ''.join(text.split()).rstrip('。；;！!')


def four_state(status):
    return 'UNKNOWN' if status == 'MISSING_RULE' else status


@pytest.fixture(scope='module')
def semantic_batch(pytestconfig):
    def read(name):
        return json.loads((TEST_ROOT / 'gold' / name).read_text(encoding='utf-8-sig'))

    document = read('工业_逐命题标准答案.json')
    mapping = read('工业_命题对齐补充.json')
    holds = read('工业_口径待确认.json')
    runs = document['runs']
    index = {run['run_id']: run for run in runs}
    assert len(index) == len(runs) == 60, '工业标准答案应有60条不同run_id'
    directory = (Path(pytestconfig.getoption('--results-dir'))
                 / 'gold_batch_reviewed' / str(time.time_ns()))
    directory.mkdir(parents=True, exist_ok=True)
    batch = dict(gold=index, mapping=mapping, holds=holds,
                 gold_version=document.get('gold_version'), directory=directory, reports=[])
    print(f'\n本轮报告目录：{directory}')
    yield batch
    case_counts = Counter(r['result'] for r in batch['reports'])
    comparisons = Counter(c['result'] for r in batch['reports'] for c in r['checks'])
    expected = sum(r['gold_claim_count'] for r in batch['reports'])
    aligned = sum(r['aligned_gold_claim_count'] for r in batch['reports'])
    summary = dict(
        evaluation_kind='development_semantic_check', formal_acceptance=False,
        model_called=False, comparison_mode='four_state', gold_version=batch['gold_version'],
        cases_reported=len(batch['reports']), case_counts=dict(case_counts),
        comparison_counts=dict(comparisons), gold_claim_count=expected,
        aligned_gold_claim_count=aligned, unaligned_gold_claim_count=expected-aligned,
        equivalent_by_four_state_mapping=sum(
            bool(c.get('equivalent_by_mapping')) for r in batch['reports'] for c in r['checks']),
        notes=['仅限本轮实际报告的工业案例，不代表保险已测试。',
               'NEEDS_ALIGNMENT和口径待确认不是已确认工程误判。',
               'MISSING_RULE在四态对比中映射UNKNOWN，原始五类状态仍保留。',
               '一对多比较项数不同于gold命题数；不计算正式准确率。'],
        cases=[{k:r[k] for k in ('case_id','run_id','result','counts','report_file')}
               for r in batch['reports']])
    path = directory / 'summary.json'
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n批量汇总已保存：{path}')


def test_gold_batch(case, evidence_engine, semantic_batch):
    b = semantic_batch
    assert case['run_id'] in b['gold'], f"找不到工业标准答案：{case['run_id']}"
    gold = b['gold'][case['run_id']]
    for field in ('case_id','user_question','ai_answer'):
        assert case[field] == gold[field], f"{case['run_id']}的{field}版本不一致"

    settings, normalize_record, analyze_run, NullLLM = evidence_engine
    copied = json.loads(json.dumps(case, ensure_ascii=False))
    artifact = analyze_run(normalize_record(copied), settings,
                           llm=NullLLM('pytest强制规则模式'), validate=True)
    assert not artifact.schema_errors, f'工程结构错误：{artifact.schema_errors}'
    graph = artifact.to_dict()['graph']
    assert graph['run_id'] == case['run_id'] and graph['case_id'] == case['case_id']
    actual = [n for n in graph['nodes'] if n['type'] == 'claim']
    assert actual, '工程未抽取任何claim'
    manual = b['mapping'].get(case['case_id'], {})
    holds = b['holds'].get(case['case_id'], {})
    gold_text_counts = Counter(normalized(c['answer_span']) for c in gold['claims'])
    checks, aligned_ids = [], set()

    for expected in gold['claims']:
        gid, span = expected['gold_claim_id'], expected['answer_span']
        base = dict(gold_claim_id=gid, gold_text=span,
                    expected_status=expected['gold_status'], rationale=expected['rationale'])
        explicit = span in manual
        if gid in holds:
            checks.append(dict(base, result='NEEDS_ALIGNMENT', reason=holds[gid]))
            continue
        if not explicit and expected.get('assessment_scope') not in (None, 'AS_ASSERTED'):
            checks.append(dict(base, result='NEEDS_ALIGNMENT', reason='范围、条件或评价对象待确认'))
            continue
        if not explicit and gold_text_counts[normalized(span)] != 1:
            checks.append(dict(base, result='NEEDS_ALIGNMENT', reason='相同文本有不同范围标注'))
            continue
        targets = manual[span] if explicit else [span]
        fully_aligned = True
        for target in targets:
            candidates = [n for n in actual if normalized(n['content']) == normalized(target)]
            check = dict(base, actual_target=target,
                         alignment_method='explicit_context_review' if explicit else 'unique_exact_text')
            if len(candidates) != 1:
                fully_aligned = False
                check.update(result='NEEDS_ALIGNMENT', candidate_count=len(candidates))
            else:
                node = candidates[0]
                observed = node.get('evidence_status')
                valid = observed in {'SUPPORT','REFUTE','UNKNOWN','CONFLICT','MISSING_RULE'}
                agrees = valid and four_state(observed) == four_state(expected['gold_status'])
                check.update(actual_claim_id=node['id'], actual_status=observed,
                             compared_expected_status=four_state(expected['gold_status']),
                             compared_actual_status=four_state(observed),
                             equivalent_by_mapping=bool(agrees and observed != expected['gold_status']),
                             result='MATCH' if agrees else 'STATUS_MISMATCH')
            checks.append(check)
        if fully_aligned:
            aligned_ids.add(gid)

    counts = Counter(c['result'] for c in checks)
    result = ('STATUS_MISMATCH' if counts['STATUS_MISMATCH'] else
              'NEEDS_ALIGNMENT' if counts['NEEDS_ALIGNMENT'] else 'MATCH')
    path = b['directory'] / f"{case['run_id']}.json"
    report = dict(case_id=case['case_id'], run_id=case['run_id'],
                  evaluation_kind='development_semantic_check', formal_acceptance=False,
                  model_called=False, comparison_mode='four_state',
                  gold_review_status=gold.get('review_status'),
                  gold_claim_count=len(gold['claims']), aligned_gold_claim_count=len(aligned_ids),
                  result=result, counts=dict(counts), checks=checks,
                  actual_claims=actual, report_file=path.name)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    b['reports'].append(report)
    assert result == 'MATCH', (
        f"{case['case_id']}：状态不符{counts['STATUS_MISMATCH']}项，"
        f"待对齐{counts['NEEDS_ALIGNMENT']}项。报告：{path}")
