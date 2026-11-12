# 新版交接契约 0.2-draft

## 版本和来源

业务材料复用PR5固定提交`8d544b865e19c5bd286e14201af777efb694b81d`，仓库`baishouxiaosheng/SYE6601-warehouse`，文件`dynamic_evidence/cases.py/tools.py/matrix.py`。未修改的原件位于vendor/pr5_dynamic，LICENSE、SOURCE.json和SHA256.json随包保留。

原材料转换：保留原句与事件值，证据ID改为不带预期含义的稳定散列，增加定位。维护原`excluded`不作为原始事实返回，改用文本所述的计划维护标记planned；它是否构成免责由审核层判断，当前PR5该字段不兼容已明确记录。缺上下文样例是为演示不可获得上下文的状态而冻结的开发变体，不宣称从真实企业截取。

## 注册表与权限

| source | tool_name | 权限、错误与分页 |
|---|---|---|
| POLICY_DB | get_policy | 合成管理员配置，可403/超时/旧版/强制空首面 |
| INCIDENT_DB | get_incident | 同上；原始duration_minutes保留 |
| CRM_CONTRACT_DB | get_customer_contract | 正常每页1条；可403/超时/旧版/空首面 |
| MAINTENANCE_CALENDAR | list_maintenance | 可完整空集或分页，不能直接证明无免责 |
| TICKET_DB | PR5_ticket_provider | 委托PR5实现；校验返回客户/事故，保留原回执 |

所有faults与bundle选择属于环境初始化，只由测试或集成程序提供。不能由建链模型根据答案自由选取。task中的scenarios、candidate_answer、expected_*不被复制到工具回执；建链器自行接收问题/候选回答，不由工具把它们变为事实。

初始化：`create_provider(bundle_id='bundle-01', faults={...}, fetched_at=..., log_path=...)`。
运行：`provider(source, task, page=None)`；Loop A若有自己的调用编号，可用`provider.query(..., call_id='...')`。
工具不自动翻页、重试、选择缺口或转人工。默认费用每次1个模拟单位，失败也计费；不得再把嵌套upstream_receipt.cost_units加一次。

## 运行材料与开发路由隔离

`runtime_data/`只有冻结原文、记录和不带答案的资料选择表；没有gold_graph、expected_obligations、expected_supports、final_decision。`dev_checks/fixture_map.json`记录开发变体来源，仅测试/集成脚本可读，禁止整份拼进模型提示。独立测试真值仍由测试A提供，本包没有新增独立评测gold。

五类材料演示：新增条件（bundle-01）、转引（03）、覆盖所需原始条款（01的通用60分钟与合同90分钟）、上下文不可获得（11）、金额主张无依据（04的材料未提供金额；主张由测试输入提出）。只返回条款/事实，不返回隐藏依赖边、标准图或建议。对比无工单条款（02）时，工单工具同样已注册，不能凭工具存在就断定必查。

## 定位与上下文

`locator`用Python Unicode码点半开区间start/end，**不是UTF-16偏移**。通过`provider.resolve_reference(source_id, record_id, locator)`解析片段。新字段是对原材料的定位，不是对语义关系的接纳。

本地材料context只包含当前与本run已取回的原文，不能绕过分页泄露后续材料。不可获得上下文时text=null、available=false。PR5工单原件只返回一条记录，因此上下文范围明确标为“上游返回记录本身”，不假称拥有完整工单历史。

## 查询完整性

scope_declaration描述指定客户/事故、当前冻结合成数据集内的记录覆盖。未按event_time筛掉过期记录，故time_filter_applied=false；有效期、服务范围及版本适用性由Checker核验，服务范围未签认时保持null。

本地游标绑定来源、任务、run、客户、事故、事件时间、材料与配置。错来源/跨run/非法游标返回ERROR而非完整空集。第一页为空且有游标时pagination_complete=false。完整空集仅表示这份明确限定的数据集中无匹配记录。

业务材料与状态在固定数据/配置下可复现；实际elapsed_ms、自动生成call_id和抓取时间会变化。重放时固定fetched_at和调用编号，并单独比较实测耗时。不要宣称每次真实运行JSON逐字一致。

## 原始回执

包含task_id/run_id/call_id/provider_call_id、tool_name、source_type、arguments、tool_status/status、分页、抓取时间、elapsed_ms、cost_units/cost、scope_declaration和records。兼容PR5已有回执字段；status和tool_status是同一状态的兼容表示，不是两套判定。

工具侧日志只记录实际调用。选择理由、候选缺口、建链提案、图版本变化、模型调用和停止理由仍归Loop A的action_log。

PR5控制器会重写顶层call_id；provider_call_id保留工具日志原编号，组装时保留二者映射。不能把不同run或旧图答案拼成当前最终结果。

## 人工复核包

```python
from review_handoff import make_review_packet
packet = make_review_packet(
    final_graph_snapshot, all_receipts, loop_action_log,
    attempted_rounds=loop_rounds,
    total_tool_calls=loop_total_calls,
    questions=["请核实所列权限及未决条款。"]
)
```

终止快照由Loop A提供：task_id/run_id/graph_version/answer_version、recommendation、workflow_status、stop_reason、gaps及scope_declaration。函数不自行决定升级或改结论；checking快照拒收，completed且有待人工事项也可由A显式请求。

包内保留来源、受影响主张、未决条件/转引、失败工具、原始条款和定位、所有回执、动作、轮数与总调用、停止理由及人工问题。不能用日志条数猜补查轮数；若传入的是部分回执，provided_receipts_count明确显示覆盖数量，总调用数仍由A提供。

## 已知限制

没有真实企业服务权限系统、生产并发日志锁、远程超时I/O或真实模型实验。模拟超时即时返回，不真的等待。对真实文本语义、所有隐藏规则和跨系统完整性不作保证。材料签认、维护语义映射、模型建链与独立验收需对应负责人完成。
