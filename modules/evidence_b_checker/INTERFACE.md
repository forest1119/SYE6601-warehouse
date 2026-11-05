# 交接格式草案

完整可复制JSON见 examples/normal_input.json。不要为了适配本程序改动原始业务数据；工具组给真实样例后增加字段映射层。

## 输入

| 部分 | 字段 | 含义 |
|---|---|---|
| task | task_id/customer_id/scope/incident_id | 本次任务、客户、服务和事故编号 |
| task | incident_start/incident_end | 带时区的故障开始结束时间 |
| responses | 来源名称 → 查询回执 | 每类来源一份当前完整返回 |
| rules | 规则数组 | 当前A组规则文件内容 |

查询回执包含：evidence_id、citation、source_type、customer_id、scope、incident_id、incident_start、incident_end、fetched_at、tool_status、pagination_complete、records。

- 时间必须带Z或+08:00等时区。
- tool_status为SUCCESS/TIMEOUT/ACCESS_DENIED或其他错误；SUCCESS不等于查全。
- pagination_complete必须是真正布尔值true，文字"true"不算查全。
- records必须是列表；失败或完整无记录时都是空列表，依靠状态与完整性区分。
- 每份记录和每个回执必须有唯一evidence_id与citation；POLICY:前缀留给规则。
- 单独出现一份不适用材料不能证明全库无适用材料。查询本身范围正确且完整，且不存在无法判断有效性的记录，才允许确认不存在。

## 记录类型

所有记录：evidence_id、citation、source_type、customer_id、scope、version。

| 来源 | 额外字段 |
|---|---|
| CRM_CONTRACT_DB | effective_from/to、rule_id、terms |
| PLAN_DB | effective_from/to、customer_tier、plan_type |
| FINANCE_ZONE_DB/KA_CLIENT_DB/TRIAL_ACCOUNTS_DB | effective_from/to、eligible |
| MONITORING_SYSTEM | incident_id、start、end |
| MAINTENANCE_CALENDAR | start、end、planned |
| TICKET_SYSTEM/BACKEND_LOGS | incident_id、cause_codes |

terms：allows_compensation、min_incident_minutes、deduct_maintenance、exceptions。专属合同缺字段不自动继承通用政策。

cause_codes：当前演示词表PROVIDER_FAILURE、CLIENT_CONFIG_ERROR、FORCE_MAJEURE、DDoS_ATTACK、CLIENT_MALICIOUS_ACTION。真实工具词表需要明确映射，陌生值返回UNKNOWN，不能默认非免责。

版本检查说明：合同与身份依据故障时点有效期和唯一适用记录判断；监控和原因记录依据同一事故标识及完整查询约定使用带版本的事件记录。此处尚未实现工具端的修订版本权威性证明；真实工具如果会返回多次修订，需补充历史版本/替代关系，不能仅以字符串V2较大就选中。

## 输出与Loop

current_decision为true/false/null；checker_decision是对应英文枚举。
obligation_results包含6项检查：合同、身份、规则、补偿许可、净时长、根因。
gaps保留未解决事项；blocked_by指出前置阻断；ready_for_lookup表示有来源且前置未阻断，**不是自动执行命令**。
loop_hint只是一条建议，流程轮次与实际人工升级由Loop负责。
raw_responses保存原始材料，used_policy_evidence保存引用规则原文。

## 输出与评分组

make_score_snapshot输出07A的0.1-draft格式，完整原始材料仍保留在Checker结果中。
check_payload中的checks是Checker对已经查明的结果所作的五项声明；尚未查明时保守给null，不由适配器根据资料名字猜有效性。
默认process_state=RUNNING，不把得到结论等同于Loop已结束。调用方已停止时传COMPLETED及stop_reason；确认已转人工时传ESCALATED及原因。
当前07A不支持明确结论同时ESCALATED，遇到此需求返回接口错误，等待双方升级约定。

## 格式错误与业务未知

坏JSON、重复字段、重复证据ID、非有限数字或接口结构错误属于InputError。
业务材料缺失、分页不足、无权限、合同条款不完整属于UNKNOWN。
两份有效同级资料无法裁决属于CONFLICT；单条资料无法匹配当前事故只算UNKNOWN。
