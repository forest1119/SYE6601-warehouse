"""Loop B raw-material provider. No graph, business decision or model call.

TICKET_DB is delegated exclusively to an injected PR5 provider. Historical
ticket_tools.get_ticket is never imported. Fixture/fault selection is admin-side.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
import json
import time
import uuid


REGISTRY = MappingProxyType({
    'POLICY_DB': 'get_policy', 'INCIDENT_DB': 'get_incident',
    'CRM_CONTRACT_DB': 'get_customer_contract',
    'MAINTENANCE_CALENDAR': 'list_maintenance', 'TICKET_DB': 'PR5_ticket_provider',
})
FAULTS = frozenset(('normal', 'forbidden', 'timeout', 'old_version', 'paged'))
ROOT = Path(__file__).resolve().parent / 'runtime_data'


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be text')
    moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if moment.utcoffset() is None:
        raise ValueError('Timezone required')
    return moment


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + ' must be nonempty text')


class RawEvidenceTools:
    def __init__(self, bundle_id='bundle-01', *, ticket_provider=None,
                 faults=None, runtime_root=None, log_path=None, fetched_at=None):
        self.root = Path(runtime_root) if runtime_root else ROOT
        self._bundles = json.loads((self.root / 'bundles.json').read_text(encoding='utf-8-sig'))
        self._documents = json.loads((self.root / 'documents.json').read_text(encoding='utf-8-sig'))
        if bundle_id not in self._bundles:
            raise ValueError('Unknown frozen runtime bundle')
        self._selection = deepcopy(self._bundles[bundle_id])
        self._faults = dict(faults or {})
        if any(source not in REGISTRY or mode not in FAULTS for source, mode in self._faults.items()):
            raise ValueError('Unknown source or fault mode')
        self._ticket_provider = ticket_provider
        self.log_path = Path(log_path) if log_path else None
        self._fixed_time = fetched_at
        if fetched_at is not None:
            timestamp(fetched_at)
        self._receipts = []

    @property
    def receipts(self):
        return deepcopy(self._receipts)

    def resolve_reference(self, source_id, record_id, locator):
        doc = self._documents.get(source_id)
        if not doc or not any(r.get('record_id') == record_id for r in doc['records']):
            raise ValueError('Unregistered source/record')
        if not isinstance(locator, dict) or locator.get('unit') != 'unicode_code_points':
            raise ValueError('Unsupported locator')
        start, end = locator.get('start'), locator.get('end')
        if type(start) is not int or type(end) is not int or not 0 <= start <= end <= len(doc['text']):
            raise ValueError('Invalid offsets')
        row = next(r for r in doc['records'] if r['record_id'] == record_id)
        if row['locator'] != locator:
            raise ValueError('Locator does not belong to this record')
        return doc['text'][start:end]

    def __call__(self, source, task, page=None):
        return self.query(source, task, page)

    def query(self, source, task, page=None, *, call_id=None):
        if source not in REGISTRY:
            raise ValueError('Source is outside frozen registry')
        if not isinstance(task, dict):
            raise ValueError('task must be an object')
        for name in ('task_id', 'run_id', 'customer_id', 'incident_id', 'event_time'):
            text(task.get(name), name)
        timestamp(task['event_time'])
        if page is not None and not isinstance(page, str):
            raise ValueError('page must be a cursor string or None')
        cid = call_id if call_id is not None else 'tool-' + uuid.uuid4().hex
        text(cid, 'call_id')
        if any(r['call_id'] == cid for r in self._receipts):
            raise ValueError('call_id already used in this provider')
        args = {k: task[k] for k in ('customer_id', 'incident_id', 'event_time')}
        args['page_token'] = page
        started = time.perf_counter()
        result = {
            'task_id': task['task_id'], 'run_id': task['run_id'], 'call_id': cid,
            'provider_call_id': cid,
            'tool_name': REGISTRY[source], 'source_type': source,
            'customer_id': task['customer_id'], 'incident_id': task['incident_id'],
            'arguments': args, 'status': 'SUCCESS', 'tool_status': 'SUCCESS',
            'records': [], 'pagination_complete': False, 'next_page_token': None,
            'fetched_at': self._fixed_time or datetime.now(timezone.utc).isoformat(),
            'cost_units': 1, 'cost': {'value': 1, 'unit': 'simulated_tool_unit'},
            'scope_declaration': {
                'customer_id': task['customer_id'], 'incident_id': task['incident_id'],
                'coverage': 'all configured records for this customer and incident in one frozen synthetic dataset',
                'event_time': task['event_time'], 'time_filter_applied': False,
                'service_scope': None,
                'limitation': 'Service applicability is unspecified. Effective-time validation belongs to Checker. Empty means none in this configured dataset, not none in an enterprise.',
            },
        }
        mode = self._faults.get(source, 'normal')
        if source == 'TICKET_DB':
            self._delegate_ticket(result, task, page, mode)
        elif mode in ('forbidden', 'timeout'):
            self._error(result, 'FORBIDDEN' if mode == 'forbidden' else 'TIMEOUT',
                        403 if mode == 'forbidden' else 'TOOL_TIMEOUT')
        else:
            try:
                self._local_query(result, source, task, page, mode)
            except (KeyError, TypeError, ValueError):
                self._error(result, 'ERROR', 'MATERIAL_FORMAT_ERROR')
        result['elapsed_ms'] = round((time.perf_counter() - started) * 1000, 3)
        result['elapsed'] = {'value': result['elapsed_ms'], 'unit': 'ms'}
        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(result, ensure_ascii=False, allow_nan=False) + '\n')
        self._receipts.append(deepcopy(result))
        return result

    @staticmethod
    def _error(result, status, code):
        result.update(status=status, tool_status=status, error_code=code,
                      records=[], pagination_complete=False, next_page_token=None)

    def _local_query(self, result, source, task, page, mode):
        rows = []
        for sid in self._selection.get(source, []):
            for row in self._documents[sid]['records']:
                if row['customer_id'] == task['customer_id'] and row['incident_id'] == task['incident_id']:
                    rows.append(deepcopy(row))
        size = 1 if source == 'CRM_CONTRACT_DB' else max(1, len(rows))
        # Cursors bind to source, task/run, query, frozen records and fault configuration.
        key = sha256(json.dumps([source, task['task_id'], task['run_id'], result['arguments']['customer_id'],
                                task['incident_id'], task['event_time'], rows, mode],
                               sort_keys=True).encode()).hexdigest()[:24]
        if page is None:
            offset = 0
        else:
            prefix = key + ':'
            if not page.startswith(prefix) or not page[len(prefix):].isdigit():
                self._error(result, 'ERROR', 'INVALID_PAGE_TOKEN')
                return
            offset = int(page[len(prefix):])
            if mode == 'paged' and offset != 1:
                self._error(result, 'ERROR', 'INVALID_PAGE_TOKEN')
                return
            if offset < 1 or offset % size or offset > max(0, len(rows)-1):
                # paged empty-first mode uses offset=1 to enter its second page.
                if not (mode == 'paged' and offset == 1):
                    self._error(result, 'ERROR', 'INVALID_PAGE_TOKEN')
                    return
        if mode == 'paged':
            if page is None:
                result['next_page_token'] = key + ':1'
                return
            selected, complete, next_token = rows, True, None
        else:
            selected = rows[offset:offset + size]
            complete = offset + size >= len(rows)
            next_token = None if complete else key + ':' + str(offset + size)
        for row in selected:
            if mode == 'old_version':
                # Synthetic old receipt/material version. Source text remains traceable.
                row.update(version='v0', effective_from='2024-01-01T00:00:00Z',
                           effective_to='2024-12-31T23:59:59Z')
            row['call_id'] = result['call_id']
            # Do not leak an unqueried second-page clause through adjacent context.
            if row.get('context', {}).get('text') is not None:
                delivered = [old for receipt in self._receipts
                             if receipt['task_id'] == task['task_id'] and receipt['run_id'] == task['run_id']
                             and receipt['tool_status'] == 'SUCCESS'
                             for old in receipt['records'] if old.get('source_id') == row['source_id']]
                delivered += [r for r in selected if r['source_id'] == row['source_id']]
                left = min(r['locator']['start'] for r in delivered)
                right = max(r['locator']['end'] for r in delivered)
                document = self._documents[row['source_id']]['text']
                row['context'] = {'source_id': row['source_id'], 'start': left, 'end': right,
                                  'text': document[left:right], 'available': True,
                                  'coverage': 'retrieved source text only',
                                  'has_more_context': left != 0 or right != len(document)}
            if self.resolve_reference(row['source_id'], row['record_id'], row['locator']) != row['excerpt']:
                raise ValueError('Unresolvable excerpt')
        result.update(records=selected, pagination_complete=complete, next_page_token=next_token)

    def _delegate_ticket(self, result, task, page, mode):
        if self._ticket_provider is None:
            self._error(result, 'ERROR', 'TICKET_PROVIDER_NOT_CONFIGURED')
            return
        # Only the PR5 provider receives test configuration. None is exported in receipt args.
        request = {k: task[k] for k in ('task_id', 'run_id', 'customer_id', 'incident_id', 'event_time')}
        request['scenarios'] = {'TICKET_DB': mode}
        try:
            raw = self._ticket_provider('TICKET_DB', request, page)
            if not isinstance(raw, dict) or raw.get('source_type') != 'TICKET_DB':
                raise ValueError('Malformed upstream source')
            if raw.get('customer_id') != task['customer_id'] or raw.get('incident_id') != task['incident_id']:
                raise ValueError('Wrong upstream query scope')
            if type(raw.get('pagination_complete')) is not bool or not isinstance(raw.get('records'), list):
                raise ValueError('Malformed upstream page')
            status = raw.get('tool_status')
            if status not in ('SUCCESS', 'FORBIDDEN', 'TIMEOUT', 'ERROR'):
                raise ValueError('Unknown upstream status')
            if status != 'SUCCESS':
                self._error(result, status, raw.get('error_code'))
                result['upstream_receipt'] = deepcopy(raw)
                return
            token = raw.get('next_page_token')
            if raw['pagination_complete'] == (token is not None):
                raise ValueError('Contradictory page completion')
            if not raw['pagination_complete'] and (not isinstance(token, str) or not token):
                raise ValueError('Missing upstream cursor')
            rows = deepcopy(raw['records'])
            for row in rows:
                if row.get('customer_id') != task['customer_id'] or row.get('incident_id') != task['incident_id']:
                    raise ValueError('Wrong upstream record scope')
                self._locate_external(row, result['call_id'])
            result.update(records=rows, status=status, tool_status=status,
                          pagination_complete=raw['pagination_complete'], next_page_token=token,
                          upstream_receipt=deepcopy(raw))
            for row in rows:
                row['upstream_citation'] = row.get('citation')
                row['citation'] = 'synthetic://' + row['source_id'] + '/' + row['record_id']
            result['scope_declaration']['coverage'] = 'Delegated PR5 synthetic ticket records, query and returned record identities checked'
            result['scope_declaration']['upstream_implementation'] = 'PR5 SyntheticTools, fixed vendor version'
        except Exception:
            self._error(result, 'ERROR', 'UPSTREAM_TICKET_ERROR')

    def _locate_external(self, row, call_id):
        statement = row.get('statement')
        if not isinstance(statement, str) or not isinstance(row.get('evidence_id'), str):
            raise ValueError('Missing original upstream record')
        sid = 'S' + sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()[:16]
        rid = row['evidence_id']
        locator = {'unit': 'unicode_code_points', 'start': 0, 'end': len(statement)}
        row.update(source_id=sid, record_id=rid, locator=locator, excerpt=statement,
                   context={'source_id': sid, 'start': 0, 'end': len(statement), 'text': statement},
                   call_id=call_id)
        # This is a captured original upstream record, not a claim to the whole document.
        row['context']['coverage'] = 'upstream returned record only'
        self._documents[sid] = {'source_id': sid, 'source_type': 'TICKET_DB',
                                'text': statement, 'records': [deepcopy(row)]}

