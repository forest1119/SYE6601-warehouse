"""依据A组文字回复的可运行Checker。只接收结构化合成材料，不调用外部工具。"""
from copy import deepcopy
from datetime import datetime
from math import isfinite
import hashlib
import json


class InputError(ValueError):
    """输入格式有误，和业务上的UNKNOWN分开。"""


def time_value(value):
    # 时间必须有时区：Z表示UTC，+08:00表示北京时间。
    if not isinstance(value, str):
        raise InputError("时间必须是文字")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise InputError("时间格式错误：" + value) from error
    if result.tzinfo is None:
        raise InputError("时间缺少时区：" + value)
    return result


def require_text(obj, key):
    if not isinstance(obj.get(key), str) or not obj[key].strip():
        raise InputError("缺少或填错字段：" + key)
    return obj[key]


def finite_number(value):
    return type(value) in (float, int) and isfinite(value)


def merged_overlap_seconds(start, end, intervals):
    """只计算故障与维护的交集；先合并重叠维护，避免重复扣减。"""
    clipped = []
    for left, right in intervals:
        if right <= left:
            raise InputError("维护结束时间必须晚于开始时间")
        left, right = max(left, start), min(right, end)
        if left < right:
            clipped.append((left, right))
    clipped.sort()
    merged = []
    for left, right in clipped:
        if merged and left <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(right, merged[-1][1]))
        else:
            merged.append((left, right))
    return sum((right-left).total_seconds() for left, right in merged)


def run_checker_v2(task, responses, rules):
    """每次传入完整最新快照；不在函数内重试、查询或实际转人工。"""
    task, responses, rules = deepcopy(task), deepcopy(responses), deepcopy(rules)
    if not isinstance(task, dict) or not isinstance(responses, dict) or not isinstance(rules, list):
        raise InputError("task/responses需要字典，rules需要列表")
    for key in ['task_id', 'customer_id', 'scope', 'incident_id']:
        require_text(task, key)
    start, end = time_value(task.get('incident_start')), time_value(task.get('incident_end'))
    if end <= start:
        raise InputError("故障结束时间必须晚于开始时间")
    rule_map = {}
    for rule in rules:
        if not isinstance(rule, dict):
            raise InputError("每条规则必须是字典")
        rid = require_text(rule, 'rule_id')
        if not rid.startswith('RULE-'):
            raise InputError('规则编号必须使用RULE-前缀')
        if rid in rule_map:
            raise InputError("规则编号重复")
        rule_map[rid] = rule
    # 所有查询回执和材料都必须有唯一编号，方便追溯。
    seen = set()
    for source, response in responses.items():
        if not isinstance(response, dict) or not isinstance(response.get('records'), list):
            raise InputError(source + ' 需要records列表，失败时也请填空列表')
        for record in [response] + response['records']:
            if not isinstance(record, dict):
                raise InputError('记录必须是字典')
            eid = require_text(record, 'evidence_id')
            require_text(record, 'citation')
            if eid.startswith('POLICY:'):
                raise InputError('POLICY:前缀保留给规则引用')
            if eid in seen:
                raise InputError('证据编号重复：' + eid)
            seen.add(eid)

    stages = [
        ('B-CONTRACT', '确认故障当时的适用合同', ['CRM_CONTRACT_DB']),
        ('B-IDENTITY', '确认客户身份和套餐', ['PLAN_DB']),
        ('B-RULE', '确定适用规则和条款', []),
        ('B-PERMISSION', '条款允许本次补偿', []),
        ('B-DURATION', '有效故障时长达到门槛', ['MONITORING_SYSTEM']),
        ('B-CAUSE', '故障原因不属于免责范围', ['TICKET_SYSTEM', 'BACKEND_LOGS'])]
    # B前缀编号是实现提议，需团队统一；它们不是A文件原本就有的字段。
    results = {oid: {'obligation_id': oid, 'statement': statement, 'status': 'UNKNOWN',
                     'reason_codes': ['NOT_CHECKED'], 'reason': '尚未检查', 'evidence_ids': [],
                     'required_sources': sources, 'required_for_decision': True}
               for oid, statement, sources in stages}
    audits, provenance = [], []
    selected_rule = None
    metrics = {}

    def set_result(oid, status, code, reason, ids=()):
        results[oid].update(status=status, reason_codes=[code], reason=reason, evidence_ids=list(ids))

    def finish(decision=None):
        # A明确允许必要条件已被有效反驳时提前结束；仍保留未执行项及其原因。
        if decision is False:
            for item in results.values():
                if item['reason_codes'] == ['NOT_CHECKED']:
                    item.update(reason_codes=['SKIPPED_AFTER_DECISIVE_REFUTE'],
                                reason='已有充分证据否定必要条件，本轮不再检查此项',
                                required_for_decision=False)
        gaps = [deepcopy(x) for x in results.values()
                if x['status'] in ('UNKNOWN', 'CONFLICT') and x['required_for_decision']]
        all_codes = {c for x in gaps for c in x['reason_codes']}
        # 这里只给Loop提示，不能声称已经完成转人工。
        handoff = 'HUMAN_REVIEW_RECOMMENDED' if ('ACCESS_DENIED' in all_codes or 'TIMEOUT' in all_codes
                   or any(x['status'] == 'CONFLICT' for x in gaps)) else 'SUPPLEMENT_OR_CONFIRM'
        if not gaps:
            handoff = 'NO_REQUIRED_GAP'
        payload = {'task': task, 'responses': responses, 'rules': rules}
        return {'schema_version': '02B-demo-v2', 'synthetic_demo': True,
                'task_id': task['task_id'], 'current_decision': decision,
                'checker_decision': {True:'RECOMMEND_COMPENSATION', False:'DO_NOT_RECOMMEND', None:'UNDETERMINED'}[decision],
                'selected_rule_id': selected_rule, 'obligation_results': list(results.values()),
                'gaps': gaps, 'loop_hint': handoff, 'duration': metrics,
                'audits': audits, 'used_policy_evidence': provenance,
                'raw_responses': responses,
                'rules_fingerprint': hashlib.sha256(json.dumps(rules,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16],
                'snapshot_fingerprint': hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]}

    def query(source):
        """先验证查询本身。查错客户或没有翻完页，不能证明没有合同。"""
        response = responses.get(source)
        if response is None:
            return None, 'NOT_QUERIED', []
        receipt = [response['evidence_id']]
        if response.get('source_type') != source:
            return None, 'WRONG_QUERY_SOURCE', receipt
        if any(response.get(k) != task[k] for k in ['customer_id','scope','incident_id']):
            return None, 'WRONG_QUERY_SCOPE', receipt
        try:
            if time_value(response.get('incident_start')) != start or time_value(response.get('incident_end')) != end:
                return None, 'WRONG_QUERY_TIME', receipt
            fetched = time_value(response.get('fetched_at'))
            if fetched < end:
                return None, 'QUERY_BEFORE_INCIDENT_END', receipt
        except InputError:
            return None, 'INVALID_QUERY_TIME', receipt
        if response.get('tool_status') != 'SUCCESS':
            code = response.get('tool_status')
            return None, code if code in ['TIMEOUT','ACCESS_DENIED'] else 'TOOL_ERROR', receipt
        if response.get('pagination_complete') is not True:
            return None, 'INCOMPLETE_PAGINATION', receipt
        return response['records'], None, receipt

    def applicable(source, temporal=True):
        records, error, receipt = query(source)
        if error:
            return [], error, receipt
        valid, malformed = [], False
        for record in records:
            reasons = []
            if record.get('source_type') != source:
                reasons.append('WRONG_RECORD_SOURCE'); malformed = True
            # 完整且范围正确的查询中，不适用记录可排除；保留审计说明。
            if any(record.get(k) != task[k] for k in ['customer_id','scope']):
                reasons.append('RECORD_NOT_APPLICABLE')
                # 缺失身份字段不是已确认“不属于该客户”。
                if any(not isinstance(record.get(k),str) or not record[k].strip() for k in ['customer_id','scope']):
                    malformed = True
            if not isinstance(record.get('version'), str) or not record['version'].strip():
                reasons.append('MISSING_VERSION'); malformed = True
            if temporal:
                try:
                    left, right = time_value(record.get('effective_from')), time_value(record.get('effective_to'))
                    if left > right:
                        raise InputError('有效期顺序错误')
                    # 演示边界约定：包含起止时刻；跨版本故障保守返回未知。
                    if not left <= start <= right:
                        reasons.append('OUTSIDE_EFFECTIVE_TIME')
                    elif end > right:
                        reasons.append('INCIDENT_CROSSES_EFFECTIVE_BOUNDARY'); malformed = True
                except InputError:
                    reasons.append('INVALID_EFFECTIVE_TIME'); malformed = True
            audits.append({'evidence_id':record['evidence_id'], 'source_type':source,
                           'usable':not reasons, 'reason_codes':reasons})
            if not reasons:
                valid.append(record)
        # 合同中只要有无法判定有效性的记录，就不能以另一个版本或空结果替代。
        return valid, 'UNRESOLVED_RECORD_METADATA' if malformed else None, receipt

    # 第一关：合同必须查询完整。未知时逻辑上阻断后续检查。
    contracts, error, receipt = applicable('CRM_CONTRACT_DB')
    if error:
        set_result('B-CONTRACT','UNKNOWN',error,'合同查询尚未查清，不能使用通用政策兜底',receipt)
        return finish()
    if len(contracts) > 1:
        set_result('B-CONTRACT','CONFLICT','MULTIPLE_EFFECTIVE_CONTRACTS',
                   '故障时点有多份适用合同或重叠版本，尚无可执行的同级裁决规则', [x['evidence_id'] for x in contracts])
        return finish()
    contract = contracts[0] if contracts else None
    contract_ids = [contract['evidence_id']] if contract else receipt
    set_result('B-CONTRACT','SUPPORT','CONTRACT_RESOLVED',
               '已取得唯一适用合同' if contract else '正确范围内完整查询，确认没有适用合同',contract_ids)

    # 第二关：身份资料也必须是故障当时适用的版本。
    identities, error, ids = applicable('PLAN_DB')
    if error or len(identities) != 1:
        state = 'CONFLICT' if len(identities)>1 and not error else 'UNKNOWN'
        set_result('B-IDENTITY',state,error or 'IDENTITY_NOT_UNIQUE','客户身份和套餐尚未明确',ids+[x['evidence_id'] for x in identities])
        return finish()
    identity = identities[0]
    tier, plan = identity.get('customer_tier'), identity.get('plan_type')
    if not isinstance(tier,str) or not isinstance(plan,str):
        set_result('B-IDENTITY','UNKNOWN','MISSING_IDENTITY_FIELDS','缺少客户等级或套餐',[identity['evidence_id']])
        return finish()
    set_result('B-IDENTITY','SUPPORT','IDENTITY_RESOLVED','客户等级和套餐已取得',[identity['evidence_id']])

    # 合同明确指定规则；没有合同时只对A明确的普通/VIP通用回退执行。
    if contract:
        rid = contract.get('rule_id')
    elif tier in ('VIP','STANDARD','BASIC'):
        rid = 'RULE-002'
    elif tier in ('TRIAL','SANDBOX'):
        rid = 'RULE-005'
    else:
        set_result('B-RULE','UNKNOWN','FALLBACK_NOT_DEFINED','该身份无合同时的回退路线尚未明确',receipt)
        return finish()
    if rid not in rule_map:
        set_result('B-RULE','UNKNOWN','RULE_NOT_FOUND','合同关联规则不存在，不能猜测适用规则',contract_ids)
        return finish()
    rule = rule_map[rid]
    try:
        left=time_value(rule['effective_time']['start']);right=time_value(rule['effective_time']['end'])
        tiers=rule['scope']['customer_tier'];plans=rule['scope']['plan_type']
        match = tier in tiers and (plan in plans or 'ALL' in plans)
        if not contract and tier=='VIP' and rid=='RULE-002':
            match = True  # A明确：VIP在确认无适用合同后可按普通客户政策处理。
        if not match or not left <= start <= end <= right:
            set_result('B-RULE','UNKNOWN','RULE_SCOPE_OR_TIME_MISMATCH','尚未锁定适用于本客户和故障时间的规则',contract_ids)
            return finish()
    except (KeyError,TypeError,InputError):
        set_result('B-RULE','UNKNOWN','INVALID_RULE_FIELDS','规则范围或时间字段不完整')
        return finish()
    # 金融/KA/试用身份必须额外取得原义务文件要求的专门来源。
    special_source={'RULE-003':'FINANCE_ZONE_DB','RULE-004':'KA_CLIENT_DB','RULE-005':'TRIAL_ACCOUNTS_DB'}.get(rid)
    special_ids=[]
    if special_source:
        special_records,error,special_ids=applicable(special_source)
        if error or len(special_records)!=1 or special_records[0].get('eligible') is not True:
            set_result('B-RULE','UNKNOWN',error or 'SPECIAL_IDENTITY_UNPROVEN','专门身份资料尚未充分确认',special_ids)
            return finish()
        special_ids += [special_records[0]['evidence_id']]
    selected_rule=rid
    policy_id='POLICY:'+rid
    provenance.append({'evidence_id':policy_id,'citation':'A组 rules.json#'+rid,'rule':deepcopy(rule)})
    set_result('B-RULE','SUPPORT','RULE_LOCKED','已锁定规则；专属合同条款优先',contract_ids+special_ids+[policy_id])

    if rid=='RULE-005':
        # 不拿999999当正常阈值，而按A原规则文字“不提供SLA赔偿”执行。
        set_result('B-PERMISSION','REFUTE','TRIAL_NO_COMPENSATION','适用免费试用/沙盒免赔规则',special_ids+[policy_id])
        return finish(False)
    if contract:
        terms=contract.get('terms')
        if not isinstance(terms,dict) or type(terms.get('allows_compensation')) is not bool:
            set_result('B-PERMISSION','UNKNOWN','MISSING_CONTRACT_TERMS','合同没有明确补偿许可，不能用通用条款填空',contract_ids)
            return finish()
        if not terms['allows_compensation']:
            set_result('B-PERMISSION','REFUTE','EXCLUSIVE_CONTRACT_DENIES','有效专属合同明确不允许本次补偿',contract_ids)
            return finish(False)
        # 必须明确条款，不擅自继承通用政策缺省值。
        threshold=terms.get('min_incident_minutes');deduct=terms.get('deduct_maintenance');exceptions=terms.get('exceptions')
    else:
        threshold=rule.get('thresholds',{}).get('min_incident_minutes')
        exceptions=rule.get('exceptions')
        # RULE-002描述未要求维护扣除；A回复要求按每条规则执行。
        deduct=False
    if not finite_number(threshold) or threshold<=0 or type(deduct) is not bool or not isinstance(exceptions,list) or not all(isinstance(x,str) and x for x in exceptions):
        set_result('B-PERMISSION','UNKNOWN','INCOMPLETE_COMPENSATION_TERMS','门槛、维护处理或免责清单未明确，禁止静默填补',contract_ids+[policy_id])
        return finish()
    if 'ALL_EXCEPTIONS' in exceptions:
        set_result('B-PERMISSION','UNKNOWN','UNSUPPORTED_EXCEPTION_WILDCARD','通配免责条款需要明确含义，不能当普通原因代码处理',contract_ids)
        return finish()
    set_result('B-PERMISSION','SUPPORT','COMPENSATION_TERMS_PRESENT','已取得明确补偿条件，仍需核实故障事实',contract_ids+[policy_id])

    # 第三关：故障区间必须与任务一致，不能拿其他事故的时长。
    incidents,error,ids=applicable('MONITORING_SYSTEM',temporal=False)
    if error or not incidents:
        set_result('B-DURATION','UNKNOWN',error or 'MISSING_INCIDENT','缺少有效故障记录',ids)
        return finish()
    for record in incidents:
        try:
            if record.get('incident_id') != task['incident_id'] or time_value(record.get('start'))!=start or time_value(record.get('end'))!=end:
                raise InputError('故障记录与任务区间不一致')
        except InputError:
            set_result('B-DURATION','UNKNOWN','INCIDENT_TIME_MISMATCH','故障区间与任务不一致，需核实',[x['evidence_id'] for x in incidents])
            return finish()
    evidence_ids=[x['evidence_id'] for x in incidents]
    maintenance_seconds=0
    if deduct:
        results['B-DURATION']['required_sources'].append('MAINTENANCE_CALENDAR')
        maintenance,error,receipts=applicable('MAINTENANCE_CALENDAR',temporal=False)
        if error:
            set_result('B-DURATION','UNKNOWN',error,'维护查询未完成，不能确认净故障时长',receipts)
            return finish()
        evidence_ids+=receipts
        intervals=[]
        for record in maintenance:
            try:
                if type(record.get('planned')) is not bool:
                    raise InputError('缺少是否计划维护的标记')
                left,right=time_value(record.get('start')),time_value(record.get('end'))
                if right<=left:
                    raise InputError('维护区间错误')
                if record['planned']:
                    intervals.append((left,right))
                evidence_ids.append(record['evidence_id'])
            except InputError:
                set_result('B-DURATION','UNKNOWN','INVALID_MAINTENANCE_RECORD','维护时间或属性不明确，不能计算净时长',receipts)
                return finish()
        maintenance_seconds=merged_overlap_seconds(start,end,intervals)
    total_seconds=(end-start).total_seconds()
    net_seconds=total_seconds-maintenance_seconds
    metrics.update(raw_minutes=total_seconds/60,maintenance_minutes=maintenance_seconds/60,
                   net_minutes=net_seconds/60,threshold_minutes=threshold)
    met=net_seconds >= threshold*60
    set_result('B-DURATION','SUPPORT' if met else 'REFUTE',
               'DURATION_THRESHOLD_MET' if met else 'DURATION_BELOW_THRESHOLD',
               f'总时长{total_seconds/60:g}分钟，扣维护{maintenance_seconds/60:g}分钟，净时长{net_seconds/60:g}分钟，门槛{threshold:g}分钟',evidence_ids)
    if not met:
        return finish(False)

    # 第四关：工单/排查报告与后台日志需共同核实根因。
    # 工单记录承载排查报告结果，真实字段仍需要Loop B给适配样例。
    cause_values=[];cause_ids=[]
    for source in ['TICKET_SYSTEM','BACKEND_LOGS']:
        records,error,ids=applicable(source,temporal=False)
        if error or not records:
            set_result('B-CAUSE','UNKNOWN',error or 'MISSING_CAUSE_EVIDENCE','故障原因资料不齐，不能默认没有免责原因',ids)
            return finish()
        for record in records:
            causes=record.get('cause_codes')
            if record.get('incident_id')!=task['incident_id'] or not isinstance(causes,list) or not causes or not all(isinstance(x,str) and x for x in causes):
                set_result('B-CAUSE','UNKNOWN','INVALID_CAUSE_RECORD','需要同一故障明确的非空根因列表',[record['evidence_id']])
                return finish()
            # 演示适配层使用明确的原因枚举；陌生文字不能自动算作非免责。
            known_causes={'PROVIDER_FAILURE','CLIENT_CONFIG_ERROR','FORCE_MAJEURE','DDoS_ATTACK','CLIENT_MALICIOUS_ACTION'}
            if any(c not in known_causes for c in causes):
                set_result('B-CAUSE','UNKNOWN','UNMAPPED_CAUSE_CODE','原因代码尚未映射，请工具组确认含义',[record['evidence_id']])
                return finish()
            cause_values.append(set(causes));cause_ids.append(record['evidence_id'])
    if any(value!=cause_values[0] for value in cause_values):
        set_result('B-CAUSE','CONFLICT','CAUSE_CONFLICT','工单与后台日志对根因的描述不一致，不能自行挑一份',cause_ids)
        return finish()
    excluded=bool(cause_values[0]&set(exceptions))
    set_result('B-CAUSE','REFUTE' if excluded else 'SUPPORT',
               'EXCLUDED_CAUSE' if excluded else 'NO_EXCLUDED_CAUSE',
               '已命中适用免责原因' if excluded else '两类资料一致，根因未命中免责清单',cause_ids)
    return finish(not excluded)
