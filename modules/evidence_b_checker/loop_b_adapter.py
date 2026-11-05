"""对接loop-b-mock分支d74ec4e；保留原始数据，不猜合同条款和服务范围。"""
from copy import deepcopy
import hashlib
import json
from checker_api import check_payload
from checker_v2 import InputError,time_value
SOURCES={'CRM_CONTRACT_DB','MAINTENANCE_CALENDAR'}

def merge_loop_b_pages(task,source,calls):
    """calls由Loop显式提供，每项含request和response；本函数不自动查询。"""
    if source not in SOURCES:raise InputError('适配器暂只支持合同和维护工具')
    raw=deepcopy(calls);records=[];issues=[];seen_ids=set();expected_token=None;finished=False
    status='SUCCESS';timestamps=[]
    if not calls:return None,[],raw
    for index,call in enumerate(calls):
        if not isinstance(call,dict) or not isinstance(call.get('request'),dict) or not isinstance(call.get('response'),dict):
            raise InputError('每次调用需要request和response字典')
        req,res=call['request'],call['response']
        if index and req.get('scenario','normal')!=calls[0]['request'].get('scenario','normal'):
            issues.append('MIXED_PAGE_SCENARIOS')
        if finished:raise InputError('完整查询后不可追加分页')
        if req.get('customer_id')!=task['customer_id'] or res.get('customer_id')!=task['customer_id']:issues.append('WRONG_CUSTOMER_QUERY')
        if res.get('source_type')!=source:issues.append('WRONG_QUERY_SOURCE')
        if req.get('page_token')!=expected_token:issues.append('BROKEN_PAGE_CHAIN')
        try:timestamps.append(time_value(res.get('fetched_at')))
        except InputError:issues.append('INVALID_FETCHED_AT')
        if res.get('tool_status')!='SUCCESS':
            status='ACCESS_DENIED' if res.get('tool_status')=='FORBIDDEN' or res.get('error_code')==403 else res.get('tool_status')
            if status not in ('ACCESS_DENIED','TIMEOUT'):status='ERROR'
            if index!=len(calls)-1:raise InputError('失败后重试请另传完整新快照')
            break
        if not isinstance(res.get('records'),list):raise InputError('records必须是列表')
        for record in res['records']:
            if not isinstance(record,dict):raise InputError('记录必须是字典')
            eid=record.get('evidence_id')
            if not isinstance(eid,str) or not eid or eid in seen_ids:raise InputError('证据编号缺失或分页重复')
            seen_ids.add(eid);records.append(deepcopy(record))
        complete=res.get('pagination_complete');token=res.get('next_page_token')
        if type(complete) is not bool:issues.append('INVALID_PAGINATION_FLAG')
        if complete is True:
            if token is not None:issues.append('CONTRADICTORY_PAGE_END')
            finished=True
        else:
            if not isinstance(token,str) or not token:issues.append('MISSING_NEXT_PAGE_TOKEN')
            if token is not None and token==req.get('page_token'):issues.append('REPEATED_PAGE_TOKEN')
            expected_token=token
    signature=hashlib.sha256(json.dumps(raw,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
    # 源码按客户过滤整个模拟数据集，覆盖当前客户；不是按任务服务过滤。
    # 这里的scope是覆盖任务的查询上下文，原始请求完整保存在raw_tool_calls。
    receipt={**deepcopy(task),'evidence_id':'LOOPB-Q-'+signature,'citation':'loop-b-mock://query/'+signature,
             'source_type':source,'tool_status':status if not issues else 'ERROR',
             'pagination_complete':finished and not issues and status=='SUCCESS','records':records,
             'fetched_at':timestamps[-1].isoformat() if timestamps else None,
             'query_coverage':'CUSTOMER_WIDE_SYNTHETIC_DATASET',
             'actual_request_fields':['customer_id','scenario','page_token'],'adapter_issues':issues}
    return receipt,issues,raw


def adapt_loop_b(task,calls_by_source,rules):
    """转换已知字段，缺少业务字段时列缺口，不补造业务事实。"""
    normalized={};gaps=[];raw={};metadata=[]
    for source,calls in calls_by_source.items():
        receipt,issues,raw_calls=merge_loop_b_pages(task,source,calls);raw[source]=raw_calls
        if receipt is None:continue
        for code in issues:gaps.append({'source_type':source,'evidence_id':receipt['evidence_id'],'code':code,'field':None})
        for record in receipt['records']:
            eid=record['evidence_id'];original_scope=deepcopy(record.get('scope'))
            # 客户范围字典不等于服务范围，不能直接改成CLOUD_SERVER。
            service=record.get('service_scope')
            if isinstance(original_scope,str):service=original_scope
            if not isinstance(service,str) or not service.strip():
                service=None;gaps.append({'source_type':source,'evidence_id':eid,'code':'MISSING_SERVICE_SCOPE','field':'scope/service_scope'})
            record['scope']=service;record['original_scope']=original_scope
            time_state=None
            try:
                start=time_value(task['incident_start']);left=time_value(record.get('effective_from'));right=time_value(record.get('effective_to'))
                time_state=left<=start<=right if left<=right else None
            except InputError:pass
            metadata.append({'evidence_id':eid,'customer_match':record.get('customer_id')==task['customer_id'],
                             'time_valid_at_incident':time_state,'version_label':record.get('version'),
                             'service_scope_known':service is not None,
                             'note':'局部元数据观察不是最终SUPPORT，版本标签大小不是有效性依据'})
            if source=='CRM_CONTRACT_DB':
                for field in ['rule_id','terms']:
                    if field not in record:gaps.append({'source_type':source,'evidence_id':eid,'code':'MISSING_CONTRACT_BUSINESS_FIELD','field':field})
                if 'statement' in record:gaps.append({'source_type':source,'evidence_id':eid,'code':'UNSTRUCTURED_STATEMENT_NOT_JUDGED','field':'statement'})
            else:
                for new,old in [('start','maintenance_start'),('end','maintenance_end')]:
                    if new not in record and old in record:record[new]=record[old]
                if type(record.get('planned')) is not bool:gaps.append({'source_type':source,'evidence_id':eid,'code':'MISSING_PLANNED_FLAG','field':'planned'})
        normalized[source]=receipt
    checker=check_payload({'task':task,'responses':normalized,'rules':rules})
    return {'integration_version':'loop-b-d74ec4e-to-02b-0.1-draft','synthetic_demo':True,
            'source_commit':'d74ec4e7927dc92dd7e65adfb7bf430df59164a5',
            'raw_tool_calls':raw,'normalized_responses':normalized,'adapter_gaps':gaps,
            'metadata_observations':metadata,'checker_result':checker}
