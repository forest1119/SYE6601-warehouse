# 动态证据接口草案

当前集成使用 PR #9 合入的 Loop B 公共包入口。团队的 GraphProposal Schema 是独立协议，接入可执行建链器后在 builder 边界做字段映射。

| 对象 | 字段 |
|---|---|
| Task | task_id、question、customer_id、incident_id、带时区的 event_time、可选 candidate_answer、可选 scenarios/source_versions。Loop 每次创建 run_id |
| Tool | 调用 source、task、page。返回 source_type、customer_id、可选 incident_id、tool_status、records、pagination_complete、next_page_token、fetched_at、可选 cost_units/error_code |
| Record | evidence_id、source_type、customer_id、可选 incident_id/scope、version、effective_from/to、citation、statement 与原始事件字段。所有时间含时区 |
| Proposal | claims[{kind,text}]、conditions[{record_id,kind,value,excerpt}]。模型输出是候选记录，正式节点 ID 由审核器分配 |
| Graph | task_id/run_id/graph_version、nodes、edges、gaps、checks、changes、coverage、rule_expression、scope_declaration、recommendation |
| Bundle | graph、history、answer、scorecard、action_log、tool_receipts、model_calls、proposals、escalation、usage、budget、mode、strategy |

## 细节

- 工具来源白名单为 POLICY_DB、INCIDENT_DB、CRM_CONTRACT_DB、MAINTENANCE_CALENDAR、TICKET_DB。只接受成功、禁止、超时、错误四种工具状态。完整空集与不可访问必须分开。
- 事件数值为原始证据字段，时长用非负整分钟，工单时间用带时区的时间戳。合同和政策须有原文，来源顺序和字段适配集中在 tools.py 与 graph.py。
- 工具返回的 scope 有 customer_id 或 incident_id 时需要匹配。可用 task.source_versions 指定期望版本。本原型无真实合同版本目录，默认检查版本存在和生效区间。同优先级出现相反阈值则留作冲突。
- 图使用 claim、obligation、rule、fact、evidence。关系支持 depends_on、derived_from、supports、refutes、overrides。当前受限表达式是 AND，其他复杂表达进入未展开复核。
- review_status 与四态分开。rejected/unresolved 表示关系审核情况，SUPPORT/REFUTE/UNKNOWN/CONFLICT 表示命题证据情况。引用通过 source_id/record_id/locator/excerpt/call_id 回到工具回执。
- snapshot 中 history 保留正式各版图。顶层 graph 补充终止状态和答案版本。最终图、答案和成绩单绑定 task_id/run_id/graph_version/answer_version。动态生成答案目前使用受限模板。
- 每轮只针对一个缺口，分页和一次超时重试都计入工具调用。终止仍输出已取得的回执和成绩单。升级包还保留失败调用 ID 和复核建议。
- 正常字段适配在 LoopBAdapter 或 Harness 注入的 builder/reviewer 完成。不要让模型用自由文本指定工具、改写业务状态、决定跳过必查或读取评测真值。

## 待团队确认

1. 专属合同覆盖边界、维护适用语义、工单期限起算点、金额与程序主张的纳入范围。
2. 原始文档切片及相邻上下文、转引查询、版本权威表、完整空集和分页语义。
3. 模型/工具预算与限制、团队公共 schema、置信度措辞和正式测量口径。
4. 测试 A 独立复核真值，测试 B 冻结评测配置。复核体验需要真实参与者，独立于模型运行。
