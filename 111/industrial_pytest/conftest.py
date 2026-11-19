import importlib
import json
from pathlib import Path
import pytest
from trace_support import load_dataset

ROOT = Path(__file__).resolve().parent


def pytest_addoption(parser):
    group = parser.getgroup('industrial-logs')
    group.addoption('--dataset', default=str(ROOT / 'data' / 'industrial_logs.json'))
    group.addoption('--expected-count', type=int, default=60)
    group.addoption('--run-interface', action='store_true', help='Explicitly enable evaluation calls')
    group.addoption('--adapter', default='', help='Python module:function accepting one full case')
    group.addoption('--expected', default='', help='Optional separate JSON: run_id -> prediction expectations')
    group.addoption('--results-dir', default=str(ROOT / 'results'))
    group.addoption("--graph-contract",action="store_true",help="检查适配后的建链结果结构")

def pytest_configure(config):
    try:
        config._trace_dataset = load_dataset(config.getoption('--dataset'))
        expected_path = config.getoption('--expected')
        config._trace_expected = json.loads(Path(expected_path).read_text(encoding='utf-8-sig')) if expected_path else None
        if config._trace_expected is not None:
            if not isinstance(config._trace_expected, dict):
                raise ValueError('Expected file must map run_id to expectation object')
            run_ids = {a['run_id'] for a in config._trace_dataset}
            if set(config._trace_expected) != run_ids:
                raise ValueError('Expected file must cover every run_id exactly; no missing/extra entries')
            if not all(isinstance(v, dict) and v for v in config._trace_expected.values()):
                raise ValueError('Every expectation must be a nonempty object')
        if config.getoption('--run-interface') and not config.getoption('--adapter'):
            raise ValueError('--run-interface requires --adapter module:function')
        if (
            config.getoption("--graph-contract")
            and not config.getoption("--run-interface")
        ):
            raise ValueError(
                "--graph-contract需要同时提供--run-interface"
            )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise pytest.UsageError(f'Dataset/configuration error: {exc}') from exc


def pytest_generate_tests(metafunc):
    if 'case' in metafunc.fixturenames:
        data = metafunc.config._trace_dataset
        metafunc.parametrize('case', data, ids=[c.get('run_id', f'row-{i}') if isinstance(c, dict) else f'row-{i}' for i, c in enumerate(data)])


@pytest.fixture(scope='session')
def dataset(pytestconfig):
    return pytestconfig._trace_dataset


@pytest.fixture(scope='session')
def evaluator(pytestconfig):
    if not pytestconfig.getoption('--run-interface'):
        pytest.skip('Interface disabled: no real evaluation request was made')
    module, sep, name = pytestconfig.getoption('--adapter').partition(':')
    if not sep:
        pytest.fail('Adapter must use module:function syntax')
    func = getattr(importlib.import_module(module), name)
    if not callable(func):
        pytest.fail('Adapter is not callable')
    return func
