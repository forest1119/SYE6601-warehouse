# Loop B 本次新增：工具日志与人工升级单

## 这是哪部分工作

只做Loop B。原版mock_tools.py、run_demo.py和data完整保留，未修改合同或维护内容。
新增代码只在原查询外记录调用，并按Loop A明确请求整理升级单。
不计算SUPPORT/REFUTE/UNKNOWN/CONFLICT，不决定赔偿，不选择工具，不自动重试、翻页或升级。

## 在PyCharm里操作

打开整个loop_b_mock文件夹。
右键run_handoff_demo.py，选择Run：演示两次维护查询和一次合同403。
结果在handoff_results/本次唯一编号/，每次新建目录，不覆盖之前的演示。
打开calls.jsonl：一行对应一次调用。jsonl与普通json不同，不要作为单个JSON对象读取。
打开escalation_编号.json：看任务、缺口、失败工具、尝试动作、人工问题。
右键test_handoff.py，选择Run，预期12项通过。
原来的run_demo.py仍可运行原版8场景。

## 给Loop A的最小用法

```python
from loop_b_handoff import call_with_log, make_escalation, save_escalation

called = call_with_log(
    task_id="TASK-001",
    tool_name="get_customer_contract",
    parameters={"customer_id": "002", "scenario": "forbidden"},
    log_path="outputs/calls.jsonl",
)
response = called["response"]  # 原工具返回，交已有适配器/Checker
entry = called["log_entry"]   # 保存或关联到你的action_log

# 以下仅在Loop A已经决定转人工时调用
sheet = make_escalation(
    task_id="TASK-001", customer_id="002",
    reason="Loop A因合同查询403要求人工复核",
    gaps=[{"source_type": "CRM_CONTRACT_DB", "reason": "无权限"}],
    evidence_ids=[], action_log=[entry], attempted_rounds=1,
    questions=["请有权限的人员取得事故发生时适用的合同。"],
)
path = save_escalation(sheet, "outputs/escalations")
```

维护调用参数可以是 {"customer_id":"002"} 或 {"customer_id":"002","page_token":"page_2"}。
不改已有get_customer_contract/list_maintenance参数和返回字段，方便现有适配器继续用。
原build_escalation仍保留；新make_escalation使用本次wrapper的日志格式，不能直接混入旧run_demo日志。
工具日志tool_status是工具状态，不是Checker四态。Loop A的action_log仍负责选择理由、重审结果和停止理由。

## 本次记录哪些内容

call_id、task_id、tool、parameters、开始结束时间、实际耗时、模拟费用单位、请求页标记、下一页标记、分页完成标志、完整返回、工具异常。
费用是模拟单位，不是人民币或API实际账单。默认每次1单位，含失败调用，Loop A可显式传值；要与测试组统一口径。
工具执行异常记录为ERROR，不伪装成不存在；未知工具和非法包装参数直接拒绝；日志落盘失败会向调用方报错，不能当作已记录成功。

## 已验证与限制

12项开发检查通过：返回保持、日志追加、唯一调用号、分页不自动继续、403/超时不自动升级、工具异常、未知工具、日志写入失败、轮数不从调用次数猜测、跨任务日志拒绝、快照不被外部修改、升级文件不覆盖。
运行过一次3调用的升级演示。升级示例attempted_rounds=2只是Loop A占位输入，不代表团队确认的轮数定义。
没有运行全组Loop控制器，没有独立测试组验收，不代表补偿结论正确率。
日志设计为本地单进程串行演示；并发写入、崩溃恢复、生产审计未实现。
业务数据仍是旧版元数据样例，业务缺口没有被本次补齐。

## 上传GitHub

本次增量包只有以下新文件；上传到loop-b-mock分支的modules/目录：
- loop_b_mock/loop_b_handoff.py
- loop_b_mock/run_handoff_demo.py
- loop_b_mock/test_handoff.py
- loop_b_mock/HANDOFF.md
- loop_b_mock/.gitignore

原PR若仍开放，同一分支新增提交会更新PR #2，不用重复新建PR。
不要上传.idea、__pycache__或handoff_results本地运行目录。
建议提交标题：Add Loop B tool-call logging and escalation handoff

## 组会可说

本次新增了Loop B调用日志包装和人工核查单交接功能，保留原查询接口和业务数据。每次调用可以保存任务、参数、状态、分页、耗时和模拟费用；人工单接收Loop A提供的停止原因、缺口、证据及轮数。已通过12项开发检查和本地演示，下一步请Loop A用真实任务上下文接入。没有改业务规则、Checker或停止策略。
